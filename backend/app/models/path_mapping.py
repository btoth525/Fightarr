"""Remote path mapping — Radarr equivalent of Settings → Download Clients →
Remote Path Mappings.

When Fightarr and your download client run on different machines (or in
containers with different mount points), the path SAB reports as the completed
download folder isn't readable by Fightarr. A path mapping translates from
the client's view to Fightarr's view at import time:

  Host                    Remote (SAB sees)              Local (Fightarr sees)
  192.168.1.10            /downloads/complete/ufc        /data/usenet/complete/ufc
  192.168.1.10            /sabnzbd/complete              /mnt/downloads

If you use the TRaSH-Guides /data layout (recommended) you DO NOT need any
path mappings — the paths are identical inside both containers.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PathMapping(Base):
    __tablename__ = "path_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    host: Mapped[str] = mapped_column(String(255), default="")
    # Hostname of the download client (used purely for documentation in the
    # UI — the mapping logic matches on the remote path prefix).

    remote_path: Mapped[str] = mapped_column(String(500))
    # The path as the download client reports it (what SAB returns in
    # history.storage). MUST be a prefix of the actual download path.

    local_path: Mapped[str] = mapped_column(String(500))
    # The path as Fightarr can see it on its filesystem.

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
