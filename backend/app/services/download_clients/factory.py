"""Instantiate the right download client from a DownloadClient DB model."""

from __future__ import annotations

from app.models.download_client import DownloadClient, DownloadClientType
from app.services.download_clients.base import DownloadClientProtocol
from app.services.download_clients.deluge import DelugeClient
from app.services.download_clients.nzbget import NZBGetClient
from app.services.download_clients.qbittorrent import QBittorrentClient
from app.services.download_clients.real_debrid import RealDebridClient
from app.services.download_clients.sabnzbd import SABnzbdClient
from app.services.download_clients.transmission import TransmissionClient


def build_client(dc: DownloadClient) -> DownloadClientProtocol:
    """Return a concrete client instance for the given DownloadClient row."""
    match dc.client_type:
        case DownloadClientType.SABNZBD:
            return SABnzbdClient(dc.host, dc.api_key or "", dc.category)

        case DownloadClientType.NZBGET:
            return NZBGetClient(dc.host, dc.username or "", dc.password or "", dc.category)

        case DownloadClientType.QBITTORRENT:
            return QBittorrentClient(dc.host, dc.username or "", dc.password or "", dc.category)

        case DownloadClientType.DELUGE:
            return DelugeClient(dc.host, dc.password or "", dc.category)

        case DownloadClientType.TRANSMISSION:
            return TransmissionClient(
                dc.host, dc.username or None, dc.password or None, dc.category
            )

        case DownloadClientType.REAL_DEBRID:
            return RealDebridClient(dc.api_key or "", dc.category)

        case _:
            raise ValueError(f"Unknown client type: {dc.client_type}")
