"""ECU Version Store and Rollback Service (Rule 10).

Guarantees:
1. Never overwrites an ECU file.
2. Every modification is saved as an immutable, new version file (e.g. ecu_v1.py, ecu_v2.py).
3. Maintains full metadata and SHA-256 hash in SQLite ecu_versions table.
4. Supports instantaneous rollback to any past version.
"""

from pathlib import Path
from typing import Optional, List, Dict
import hashlib
import difflib
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models.db import EcuVersion, SessionLocal

# Default ECU controller template (Headlamp ECU baseline logic)
BASELINE_ECU_CODE = '''"""Simulated Headlamp ECU Controller (Automotive Logic)."""

from typing import Dict, Any, Tuple


class HeadlampECU:
    """Headlamp Electronic Control Unit simulation."""

    def __init__(self, hi_speed_threshold: float = 40.0, hi_lux_threshold: float = 50.0, day_lux_threshold: float = 1000.0):
        self.hi_speed_threshold = hi_speed_threshold
        self.hi_lux_threshold = hi_lux_threshold
        self.day_lux_threshold = day_lux_threshold

    def evaluate(self, telemetry: Dict[str, Any]) -> Tuple[str, str]:
        """Evaluate vehicle sensor inputs and decide headlamp state.

        States:
        - OFF: Daytime or disabled
        - LOW: Low beam (standard passing beam, oncoming traffic, or low speed)
        - HIGH: High beam (main beam when dark and no vehicle ahead)
        - FALLBACK: Sensor failure default mode
        """
        speed = telemetry.get("speed", 0.0)
        speed_valid = telemetry.get("speed_valid", True)
        lux = telemetry.get("lux", 0.0)
        camera_valid = telemetry.get("camera_valid", True)
        oncoming = telemetry.get("oncoming", False)

        # Fallback if camera sensor fails
        if not camera_valid:
            return "FALLBACK", "Camera signal lost, low beam fallback"

        # Ignore invalid speed frame
        effective_speed = speed if speed_valid else 0.0

        # Daylight shut-off
        if lux > self.day_lux_threshold:
            return "OFF", f"Daylight, above {self.day_lux_threshold} lux"

        # Oncoming vehicle anti-glare
        if oncoming:
            return "LOW", "Oncoming vehicle detected within 150 m"

        # High beam activation
        if effective_speed >= self.hi_speed_threshold and lux < self.hi_lux_threshold:
            return "HIGH", f"Road clear, {self.hi_speed_threshold} km/h or more, dark"

        if effective_speed < self.hi_speed_threshold:
            return "LOW", f"Below {self.hi_speed_threshold} km/h high-beam threshold"

        return "LOW", f"Light level above {self.hi_lux_threshold} lux"
'''


class EcuStore:
    """Manages versioned ECU source files and safe rollback."""

    def __init__(self, storage_dir: Optional[Path] = None, db_session: Optional[Session] = None):
        if storage_dir is None:
            backend_dir = Path(__file__).resolve().parent.parent
            self.storage_dir = backend_dir / "ecu" / "versions"
        else:
            self.storage_dir = Path(storage_dir)

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._session = db_session

    def _get_session(self) -> Session:
        return self._session if self._session is not None else SessionLocal()

    def _calculate_hash(self, content: str) -> str:
        """Compute SHA-256 hash of code content."""
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

    def get_latest_version_number(self) -> int:
        """Determine highest existing version number from DB and disk."""
        session = self._get_session()
        db_max = 0
        try:
            latest = session.query(EcuVersion).order_by(EcuVersion.version_id.desc()).first()
            if latest:
                db_max = latest.version_id
        finally:
            if self._session is None:
                session.close()

        disk_max = 0
        if self.storage_dir.exists():
            import re
            for p in self.storage_dir.glob("ecu_v*.py"):
                m = re.search(r"ecu_v(\d+)\.py", p.name)
                if m:
                    disk_max = max(disk_max, int(m.group(1)))

        return max(db_max, disk_max)

    def initialize_baseline(self) -> EcuVersion:
        """Seed baseline v1 version if no version exists."""
        session = self._get_session()
        try:
            existing = session.query(EcuVersion).first()
            if existing:
                active = session.query(EcuVersion).filter(EcuVersion.is_active == True).first()
                return active or existing

            return self.save_new_version(
                code_content=BASELINE_ECU_CODE,
                description="Baseline Headlamp ECU controller (v1 initial)",
                author="system",
                set_active=True,
            )
        finally:
            if self._session is None:
                session.close()

    def save_new_version(
        self,
        code_content: str,
        description: str,
        author: str = "agent",
        set_active: bool = True,
    ) -> EcuVersion:
        """Save a new ECU version without overwriting any existing files (Rule 10)."""
        session = self._get_session()
        try:
            next_ver_num = self.get_latest_version_number() + 1
            version_tag = f"v{next_ver_num}"
            filename = f"ecu_{version_tag}.py"
            file_path = self.storage_dir / filename

            # Strict Rule 10 check: file must not already exist
            if file_path.exists():
                raise FileExistsError(f"Target ECU version file {file_path} already exists! Rule 10 forbids overwrite.")

            # Write immutable version file
            file_path.write_text(code_content, encoding="utf-8")

            if set_active:
                session.query(EcuVersion).update({EcuVersion.is_active: False})

            code_hash = self._calculate_hash(code_content)
            version_record = EcuVersion(
                version_tag=version_tag,
                code_hash=code_hash,
                code_content=code_content,
                filename=filename,
                author=author,
                description=description,
                is_active=set_active,
                created_at=datetime.now(timezone.utc),
            )
            session.add(version_record)
            session.commit()
            session.refresh(version_record)
            return version_record
        finally:
            if self._session is None:
                session.close()

    def rollback(self, target_version_tag: str) -> EcuVersion:
        """Rollback active ECU to an earlier version tag without deleting history (Rule 10)."""
        session = self._get_session()
        try:
            target = session.query(EcuVersion).filter(EcuVersion.version_tag == target_version_tag).first()
            if not target:
                raise ValueError(f"Version {target_version_tag} not found in version store.")

            # Deactivate all, activate target
            session.query(EcuVersion).update({EcuVersion.is_active: False})
            target.is_active = True
            session.commit()
            session.refresh(target)
            return target
        finally:
            if self._session is None:
                session.close()

    def get_active_version(self) -> Optional[EcuVersion]:
        """Return the currently active ECU version record."""
        session = self._get_session()
        try:
            return session.query(EcuVersion).filter(EcuVersion.is_active == True).first()
        finally:
            if self._session is None:
                session.close()

    def list_versions(self) -> List[EcuVersion]:
        """Return all ECU versions in ascending order."""
        session = self._get_session()
        try:
            return session.query(EcuVersion).order_by(EcuVersion.version_id.asc()).all()
        finally:
            if self._session is None:
                session.close()

    def get_diff(self, version_tag_a: str, version_tag_b: str) -> str:
        """Generate a unified diff between two ECU versions."""
        session = self._get_session()
        try:
            ver_a = session.query(EcuVersion).filter(EcuVersion.version_tag == version_tag_a).first()
            ver_b = session.query(EcuVersion).filter(EcuVersion.version_tag == version_tag_b).first()

            if not ver_a or not ver_b:
                raise ValueError("Both version tags must exist to compute diff.")

            lines_a = ver_a.code_content.splitlines(keepends=True)
            lines_b = ver_b.code_content.splitlines(keepends=True)

            diff = difflib.unified_diff(
                lines_a,
                lines_b,
                fromfile=f"ecu_{version_tag_a}.py",
                tofile=f"ecu_{version_tag_b}.py",
            )
            return "".join(diff)
        finally:
            if self._session is None:
                session.close()
