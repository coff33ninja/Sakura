"""
Speaker Recognition and Authentication for Sakura
Voice authentication - only respond to authorized speaker(s)

Rules followed:
- All imports MUST be used
- Async with asyncio.Lock() for thread safety
- aiofiles for file I/O
- Database integration for speaker profiles
"""
import asyncio
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import aiofiles
from pathlib import Path

try:
    from tools.base import BaseTool, ToolResult, ToolStatus
except ImportError:
    from ..base import BaseTool, ToolResult, ToolStatus

try:
    from modules.database import get_database, HAS_AIOSQLITE
except ImportError:
    HAS_AIOSQLITE = False
    get_database = None


class AuthenticationMode(Enum):
    """Speaker authentication modes"""
    DISABLED = "disabled"      # No authentication
    OPTIONAL = "optional"      # Authenticate but continue if fails
    STRICT = "strict"          # Reject if speaker not authenticated
    TRAINING = "training"      # Recording mode - learn new speaker


@dataclass
class SpeakerProfile:
    """Speaker voice profile for authentication"""
    speaker_id: str
    name: str
    created_at: str
    updated_at: str
    confidence_threshold: float = 0.75
    samples_count: int = 0
    is_owner: bool = False
    features: List[List[float]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthenticationResult:
    """Result of speaker authentication"""
    authenticated: bool
    speaker_id: Optional[str] = None
    speaker_name: Optional[str] = None
    confidence: float = 0.0
    is_owner: bool = False
    reason: str = ""
    audio_quality: float = 0.0


class SpeakerAuthentication(BaseTool):
    """Speaker recognition and authentication tool
    
    Voice-based authentication system that learns and recognizes authorized speakers.
    
    Modes of Operation:
        DISABLED: No authentication checks, respond to anyone
        OPTIONAL: Attempt authentication but continue if it fails
        STRICT: Only respond to authenticated speakers, reject unknown voices
        TRAINING: Record speaker samples to build voice profile
    
    Example Usage:
        # Initialize speaker auth
        auth = SpeakerAuthentication()
        await auth.initialize()
        
        # Train a speaker
        await auth.train_speaker(
            speaker_id="user_001",
            name="John",
            audio_chunks=[...audio_data...],
            is_owner=True
        )
        
        # Authenticate incoming audio
        result = await auth.authenticate(audio_chunk)
        if result.authenticated:
            # Process request from identified speaker
            process_request(result.speaker_id)
        else:
            # Unknown or unauthorized speaker
            reject_request(f"Speaker not recognized. Confidence: {result.confidence}")
    
    Features:
        - Voice profile training with multiple samples
        - Real-time speaker authentication
        - Confidence scoring with configurable thresholds
        - Owner identification for privilege operations
        - Audio quality assessment
        - Database persistence with JSON fallback
        - Authentication logging and history
    """
    
    name = "speaker_recognition"
    description = "Voice authentication - learn your voice and only respond to you"
    enabled = True
    
    def __init__(self):
        """Initialize speaker authentication"""
        self.profiles: Dict[str, SpeakerProfile] = {}
        self._lock = asyncio.Lock()
        self._db_manager = None
        self._auth_mode = AuthenticationMode.OPTIONAL
        self._current_speaker_id: Optional[str] = None
        self._feature_cache: Dict[str, List[float]] = {}
        self._min_audio_samples = 5
        self._min_audio_duration_ms = 500
        self._max_audio_duration_ms = 30000
        
    async def initialize(self) -> bool:
        """Initialize database and load profiles"""
        try:
            if HAS_AIOSQLITE:
                self._db_manager = await get_database()
                await self._create_schema()
                await self._load_profiles()
            await self._load_profiles_from_file()
            logging.info("✅ Speaker Recognition initialized")
            return True
        except Exception as e:
            logging.error(f"❌ Speaker Recognition initialization failed: {e}")
            return False
    
    async def _create_schema(self):
        """Create database tables for speaker profiles"""
        if not self._db_manager:
            return
        
        try:
            cursor = await self._db_manager.cursor()
            
            # Speaker profiles table
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS speaker_profiles (
                    speaker_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    is_owner BOOLEAN DEFAULT 0,
                    confidence_threshold REAL DEFAULT 0.75,
                    samples_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Speaker audio samples table
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS speaker_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    speaker_id TEXT REFERENCES speaker_profiles(speaker_id) ON DELETE CASCADE,
                    audio_hash TEXT UNIQUE,
                    duration_ms INTEGER,
                    confidence REAL,
                    features TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (speaker_id) REFERENCES speaker_profiles(speaker_id)
                )
            ''')
            
            # Authentication log
            await cursor.execute('''
                CREATE TABLE IF NOT EXISTS authentication_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    speaker_id TEXT,
                    authenticated BOOLEAN,
                    confidence REAL,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await self._db_manager.commit()
            logging.info("📊 Speaker recognition schema created")
        except Exception as e:
            logging.error(f"Failed to create schema: {e}")
    
    async def _load_profiles(self):
        """Load speaker profiles from database"""
        if not self._db_manager:
            return
        
        try:
            cursor = await self._db_manager.cursor()
            await cursor.execute('SELECT * FROM speaker_profiles')
            rows = await cursor.fetchall()
            
            for row in rows:
                profile = SpeakerProfile(
                    speaker_id=row['speaker_id'],
                    name=row['name'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    confidence_threshold=row['confidence_threshold'],
                    samples_count=row['samples_count'],
                    is_owner=bool(row['is_owner']),
                    metadata=json.loads(row['metadata'] or '{}')
                )
                self.profiles[profile.speaker_id] = profile
                
            logging.info(f"📊 Loaded {len(self.profiles)} speaker profiles")
        except Exception as e:
            logging.warning(f"Could not load profiles from DB: {e}")
    
    async def _load_profiles_from_file(self):
        """Load profiles from JSON file (fallback)"""
        profiles_file = Path("speaker_profiles.json")
        
        if profiles_file.exists():
            try:
                async with aiofiles.open(profiles_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    
                    for speaker_id, profile_data in data.items():
                        if speaker_id not in self.profiles:
                            self.profiles[speaker_id] = SpeakerProfile(**profile_data)
                
                logging.info(f"📄 Loaded {len(self.profiles)} profiles from JSON")
            except Exception as e:
                logging.warning(f"Could not load profiles from JSON: {e}")
    
    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute speaker recognition action"""
        try:
            if action == "enroll":
                return await self._enroll_speaker(**kwargs)
            elif action == "authenticate":
                return await self._authenticate_speaker(**kwargs)
            elif action == "list_profiles":
                return await self._list_profiles()
            elif action == "remove_profile":
                return await self._remove_profile(**kwargs)
            elif action == "set_auth_mode":
                return await self._set_auth_mode(**kwargs)
            elif action == "get_auth_mode":
                return await self._get_auth_mode()
            elif action == "set_current_speaker":
                return await self._set_current_speaker(**kwargs)
            elif action == "get_current_speaker":
                return await self._get_current_speaker()
            elif action == "verify_audio_quality":
                return await self._verify_audio_quality(**kwargs)
            elif action == "get_speaker_info":
                return await self._get_speaker_info(**kwargs)
            else:
                return ToolResult(ToolStatus.ERROR, error=f"Unknown action: {action}")
        except Exception as e:
            logging.error(f"Speaker recognition error: {e}")
            return ToolResult(ToolStatus.ERROR, error=str(e))
    
    async def _enroll_speaker(self, speaker_name: str, audio_samples: List[bytes], 
                             is_owner: bool = False, **kwargs) -> ToolResult:
        """Enroll a new speaker with voice samples"""
        async with self._lock:
            try:
                if not audio_samples:
                    return ToolResult(ToolStatus.ERROR, error="No audio samples provided")
                
                if len(audio_samples) < self._min_audio_samples:
                    return ToolResult(ToolStatus.ERROR, 
                        error=f"Need at least {self._min_audio_samples} samples, got {len(audio_samples)}")
                
                # Check audio quality
                quality_results = []
                for sample in audio_samples:
                    quality = await self._check_audio_quality(sample)
                    quality_results.append(quality)
                
                avg_quality = np.mean(quality_results)
                if avg_quality < 0.5:
                    return ToolResult(ToolStatus.ERROR, 
                        error=f"Audio quality too low: {avg_quality:.2f}/1.0. Please retake samples in quieter environment")
                
                # Extract features from samples
                all_features = []
                for sample in audio_samples:
                    features = await self._extract_features(sample)
                    if features is not None:
                        all_features.extend(features)
                
                if not all_features:
                    return ToolResult(ToolStatus.ERROR, error="Could not extract features from audio samples")
                
                # Create speaker profile
                speaker_id = f"speaker_{len(self.profiles) + 1}"
                profile = SpeakerProfile(
                    speaker_id=speaker_id,
                    name=speaker_name,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    samples_count=len(audio_samples),
                    is_owner=is_owner,
                    features=all_features,
                    metadata={"enrollment_quality": float(avg_quality)}
                )
                
                self.profiles[speaker_id] = profile
                
                # Save to database
                if self._db_manager:
                    await self._save_profile_to_db(profile)
                
                # Save to JSON
                await self._save_profiles_to_file()
                
                logging.info(f"✅ Enrolled speaker '{speaker_name}' ({speaker_id})")
                
                return ToolResult(ToolStatus.SUCCESS, 
                    data={
                        "speaker_id": speaker_id,
                        "speaker_name": speaker_name,
                        "samples_recorded": len(audio_samples),
                        "audio_quality": float(avg_quality),
                        "is_owner": is_owner
                    },
                    message=f"Successfully enrolled '{speaker_name}' with {len(audio_samples)} voice samples")
                
            except Exception as e:
                logging.error(f"Enrollment failed: {e}")
                return ToolResult(ToolStatus.ERROR, error=str(e))
    
    async def _authenticate_speaker(self, audio_sample: bytes, **kwargs) -> ToolResult:
        """Authenticate if audio is from enrolled speaker"""
        async with self._lock:
            try:
                if not audio_sample:
                    return ToolResult(ToolStatus.ERROR, error="No audio sample provided")
                
                if not self.profiles:
                    return ToolResult(ToolStatus.ERROR, error="No speaker profiles enrolled")
                
                # Check audio quality
                quality = await self._check_audio_quality(audio_sample)
                if quality < 0.4:
                    return ToolResult(ToolStatus.ERROR, 
                        error=f"Audio quality too low ({quality:.2f}). Cannot authenticate reliably")
                
                # Extract features
                features = await self._extract_features(audio_sample)
                if features is None or len(features) == 0:
                    return ToolResult(ToolStatus.ERROR, error="Could not extract voice features")
                
                # Compare against all profiles
                best_match = None
                best_confidence = 0.0
                
                for speaker_id, profile in self.profiles.items():
                    if not profile.features:
                        continue
                    
                    confidence = await self._compare_features(features, profile.features)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (speaker_id, profile)
                
                # Determine if authenticated
                if best_match:
                    speaker_id, profile = best_match
                    threshold = profile.confidence_threshold
                    authenticated = best_confidence >= threshold
                    
                    self._current_speaker_id = speaker_id if authenticated else None
                    
                    # Log authentication attempt
                    if self._db_manager:
                        await self._log_authentication(speaker_id, authenticated, best_confidence)
                    
                    result = AuthenticationResult(
                        authenticated=authenticated,
                        speaker_id=speaker_id if authenticated else None,
                        speaker_name=profile.name if authenticated else None,
                        confidence=best_confidence,
                        is_owner=profile.is_owner if authenticated else False,
                        audio_quality=quality,
                        reason="Voice matched" if authenticated else f"Voice didn't match (confidence: {best_confidence:.2%})"
                    )
                    
                    if authenticated:
                        logging.info(f"✅ Speaker authenticated: {profile.name}")
                    else:
                        logging.warning(f"❌ Speaker not authenticated (confidence: {best_confidence:.2%})")
                    
                    return ToolResult(ToolStatus.SUCCESS, data=result.__dict__, message=result.reason)
                else:
                    return ToolResult(ToolStatus.ERROR, error="Could not match voice to any profile")
                
            except Exception as e:
                logging.error(f"Authentication error: {e}")
                return ToolResult(ToolStatus.ERROR, error=str(e))
    
    async def _list_profiles(self) -> ToolResult:
        """List all enrolled speaker profiles"""
        async with self._lock:
            try:
                profiles_list = [
                    {
                        "speaker_id": p.speaker_id,
                        "name": p.name,
                        "is_owner": p.is_owner,
                        "samples_count": p.samples_count,
                        "created_at": p.created_at,
                        "confidence_threshold": p.confidence_threshold
                    }
                    for p in self.profiles.values()
                ]
                
                return ToolResult(ToolStatus.SUCCESS,
                    data={"profiles": profiles_list, "total": len(profiles_list)},
                    message=f"Found {len(profiles_list)} enrolled speaker(s)")
            except Exception as e:
                return ToolResult(ToolStatus.ERROR, error=str(e))
    
    async def _remove_profile(self, speaker_id: str, **kwargs) -> ToolResult:
        """Remove a speaker profile"""
        async with self._lock:
            try:
                if speaker_id not in self.profiles:
                    return ToolResult(ToolStatus.ERROR, error=f"Speaker '{speaker_id}' not found")
                
                profile = self.profiles.pop(speaker_id)
                
                # Remove from database
                if self._db_manager:
                    cursor = await self._db_manager.cursor()
                    await cursor.execute('DELETE FROM speaker_profiles WHERE speaker_id = ?', (speaker_id,))
                    await self._db_manager.commit()
                
                # Save updated profiles
                await self._save_profiles_to_file()
                
                logging.info(f"🗑️ Removed speaker profile: {profile.name}")
                
                return ToolResult(ToolStatus.SUCCESS, 
                    data={"removed_speaker": profile.name},
                    message=f"Removed '{profile.name}' from voice authentication")
            except Exception as e:
                return ToolResult(ToolStatus.ERROR, error=str(e))
    
    async def _set_auth_mode(self, mode: str, **kwargs) -> ToolResult:
        """Set authentication mode"""
        try:
            mode_upper = mode.upper()
            if mode_upper not in [m.name for m in AuthenticationMode]:
                valid_modes = ", ".join([m.name for m in AuthenticationMode])
                return ToolResult(ToolStatus.ERROR, 
                    error=f"Invalid mode. Valid modes: {valid_modes}")
            
            self._auth_mode = AuthenticationMode[mode_upper]
            logging.info(f"🔐 Authentication mode set to: {self._auth_mode.value}")
            
            return ToolResult(ToolStatus.SUCCESS,
                data={"auth_mode": self._auth_mode.value},
                message=f"Authentication mode changed to '{self._auth_mode.value}'")
        except Exception as e:
            return ToolResult(ToolStatus.ERROR, error=str(e))
    
    async def _get_auth_mode(self) -> ToolResult:
        """Get current authentication mode"""
        return ToolResult(ToolStatus.SUCCESS,
            data={"auth_mode": self._auth_mode.value},
            message=f"Current mode: {self._auth_mode.value}")
    
    async def _set_current_speaker(self, speaker_id: str, **kwargs) -> ToolResult:
        """Manually set current authenticated speaker"""
        async with self._lock:
            if speaker_id not in self.profiles:
                return ToolResult(ToolStatus.ERROR, error=f"Speaker '{speaker_id}' not found")
            
            self._current_speaker_id = speaker_id
            profile = self.profiles[speaker_id]
            
            logging.info(f"👤 Set current speaker: {profile.name}")
            
            return ToolResult(ToolStatus.SUCCESS,
                data={"speaker_id": speaker_id, "speaker_name": profile.name},
                message=f"Current speaker set to '{profile.name}'")
    
    async def _get_current_speaker(self) -> ToolResult:
        """Get current authenticated speaker"""
        async with self._lock:
            if not self._current_speaker_id:
                return ToolResult(ToolStatus.ERROR, error="No current speaker authenticated")
            
            profile = self.profiles.get(self._current_speaker_id)
            if not profile:
                self._current_speaker_id = None
                return ToolResult(ToolStatus.ERROR, error="Current speaker profile not found")
            
            return ToolResult(ToolStatus.SUCCESS,
                data={
                    "speaker_id": self._current_speaker_id,
                    "speaker_name": profile.name,
                    "is_owner": profile.is_owner
                },
                message=f"Current speaker: {profile.name}")
    
    async def _verify_audio_quality(self, audio_sample: bytes, **kwargs) -> ToolResult:
        """Verify audio quality for speaker recognition"""
        try:
            quality = await self._check_audio_quality(audio_sample)
            
            if quality >= 0.8:
                rating = "Excellent"
            elif quality >= 0.6:
                rating = "Good"
            elif quality >= 0.4:
                rating = "Fair"
            else:
                rating = "Poor"
            
            return ToolResult(ToolStatus.SUCCESS,
                data={"quality_score": quality, "rating": rating},
                message=f"Audio quality: {rating} ({quality:.2%})")
        except Exception as e:
            return ToolResult(ToolStatus.ERROR, error=str(e))
    
    async def _get_speaker_info(self, speaker_id: str, **kwargs) -> ToolResult:
        """Get information about a specific speaker"""
        async with self._lock:
            if speaker_id not in self.profiles:
                return ToolResult(ToolStatus.ERROR, error=f"Speaker '{speaker_id}' not found")
            
            profile = self.profiles[speaker_id]
            
            return ToolResult(ToolStatus.SUCCESS,
                data={
                    "speaker_id": speaker_id,
                    "name": profile.name,
                    "is_owner": profile.is_owner,
                    "samples_count": profile.samples_count,
                    "confidence_threshold": profile.confidence_threshold,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                    "metadata": profile.metadata
                },
                message=f"Information for '{profile.name}'")
    
    # Feature extraction and comparison
    
    async def _extract_features(self, audio_sample: bytes) -> Optional[List[float]]:
        """Extract voice features from audio (MFCC-like features)"""
        try:
            # Convert to numpy array
            audio_array = np.frombuffer(audio_sample, dtype=np.int16)
            
            # Normalize audio
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # Simple feature extraction: frame energy + spectral features
            frame_size = 512
            hop_size = 256
            frames = []
            
            for i in range(0, len(audio_array) - frame_size, hop_size):
                frame = audio_array[i:i + frame_size]
                
                # Frame energy
                energy = np.sqrt(np.sum(frame ** 2) / len(frame))
                
                # Zero crossing rate
                zcr = np.sum(np.abs(np.diff(np.sign(frame)))) / (2 * len(frame))
                
                # Spectral centroid (simplified)
                fft = np.abs(np.fft.fft(frame))
                if np.sum(fft) > 0:
                    centroid = np.sum(np.arange(len(fft)) * fft) / np.sum(fft)
                    centroid = centroid / len(fft)
                else:
                    centroid = 0
                
                frames.append([energy, zcr, centroid])
            
            if not frames:
                return None
            
            # Return statistical features
            frames_array = np.array(frames)
            features = []
            
            for col in range(frames_array.shape[1]):
                col_data = frames_array[:, col]
                features.extend([
                    float(np.mean(col_data)),
                    float(np.std(col_data)),
                    float(np.min(col_data)),
                    float(np.max(col_data))
                ])
            
            return features
            
        except Exception as e:
            logging.warning(f"Feature extraction error: {e}")
            return None
    
    async def _compare_features(self, features1: List[float], features2_list: List[List[float]]) -> float:
        """Compare voice features using cosine similarity"""
        try:
            if not features1 or not features2_list:
                return 0.0
            
            features1 = np.array(features1)
            
            similarities = []
            for features2 in features2_list:
                features2 = np.array(features2)
                
                # Cosine similarity
                if len(features1) != len(features2):
                    continue
                
                dot_product = np.dot(features1, features2)
                norm1 = np.linalg.norm(features1)
                norm2 = np.linalg.norm(features2)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                    # Map from [-1, 1] to [0, 1]
                    similarity = (similarity + 1) / 2
                    similarities.append(similarity)
            
            if similarities:
                return float(np.mean(similarities))
            return 0.0
            
        except Exception as e:
            logging.warning(f"Feature comparison error: {e}")
            return 0.0
    
    async def _check_audio_quality(self, audio_sample: bytes) -> float:
        """Check audio quality (0.0 to 1.0)"""
        try:
            audio_array = np.frombuffer(audio_sample, dtype=np.int16)
            
            if len(audio_array) == 0:
                return 0.0
            
            # Normalize
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # Check for clipping
            clipping_ratio = np.sum(np.abs(audio_array) > 0.99) / len(audio_array)
            clipping_score = max(0, 1 - clipping_ratio * 2)
            
            # Check for silence
            rms = np.sqrt(np.mean(audio_array ** 2))
            silence_score = min(1.0, rms * 10)  # Higher RMS = louder = better
            
            # Check for noise/distortion
            snr_estimate = 1.0 - np.std(audio_array) / (np.max(np.abs(audio_array)) + 1e-6)
            snr_score = max(0, snr_estimate)
            
            # Combined quality score
            quality = (clipping_score * 0.3 + silence_score * 0.4 + snr_score * 0.3)
            
            return float(quality)
            
        except Exception as e:
            logging.warning(f"Audio quality check error: {e}")
            return 0.5
    
    async def _save_profile_to_db(self, profile: SpeakerProfile):
        """Save speaker profile to database"""
        if not self._db_manager:
            return
        
        try:
            cursor = await self._db_manager.cursor()
            
            await cursor.execute('''
                INSERT OR REPLACE INTO speaker_profiles 
                (speaker_id, name, is_owner, confidence_threshold, samples_count, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.speaker_id,
                profile.name,
                profile.is_owner,
                profile.confidence_threshold,
                profile.samples_count,
                datetime.now().isoformat(),
                json.dumps(profile.metadata)
            ))
            
            await self._db_manager.commit()
        except Exception as e:
            logging.warning(f"Could not save profile to DB: {e}")
    
    async def _log_authentication(self, speaker_id: str, authenticated: bool, confidence: float):
        """Log authentication attempt"""
        if not self._db_manager:
            return
        
        try:
            cursor = await self._db_manager.cursor()
            
            await cursor.execute('''
                INSERT INTO authentication_log (speaker_id, authenticated, confidence)
                VALUES (?, ?, ?)
            ''', (speaker_id, authenticated, confidence))
            
            await self._db_manager.commit()
        except Exception as e:
            logging.warning(f"Could not log authentication: {e}")
    
    async def _save_profiles_to_file(self):
        """Save all profiles to JSON file for portability"""
        try:
            profiles_data = {}
            
            for speaker_id, profile in self.profiles.items():
                profiles_data[speaker_id] = {
                    "speaker_id": profile.speaker_id,
                    "name": profile.name,
                    "created_at": profile.created_at,
                    "updated_at": profile.updated_at,
                    "confidence_threshold": profile.confidence_threshold,
                    "samples_count": profile.samples_count,
                    "is_owner": profile.is_owner,
                    "features": profile.features,
                    "metadata": profile.metadata
                }
            
            async with aiofiles.open("speaker_profiles.json", 'w') as f:
                await f.write(json.dumps(profiles_data, indent=2))
            
            logging.info("💾 Speaker profiles saved to JSON")
        except Exception as e:
            logging.warning(f"Could not save profiles to JSON: {e}")
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the tool's parameter schema for Gemini function calling"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "enroll",
                        "authenticate",
                        "list_profiles",
                        "remove_profile",
                        "set_auth_mode",
                        "get_auth_mode",
                        "set_current_speaker",
                        "get_current_speaker",
                        "verify_audio_quality",
                        "get_speaker_info"
                    ],
                    "description": "Action to perform"
                },
                "speaker_name": {
                    "type": "string",
                    "description": "Name of speaker (for enroll)"
                },
                "audio_samples": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of base64-encoded audio samples (for enroll)"
                },
                "audio_sample": {
                    "type": "string",
                    "description": "Base64-encoded audio sample (for authenticate, verify_audio_quality)"
                },
                "is_owner": {
                    "type": "boolean",
                    "description": "Mark as owner account (for enroll)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["DISABLED", "OPTIONAL", "STRICT", "TRAINING"],
                    "description": "Authentication mode (for set_auth_mode)"
                },
                "speaker_id": {
                    "type": "string",
                    "description": "Speaker ID (for remove_profile, set_current_speaker, get_speaker_info)"
                }
            },
            "required": ["action"]
        }
