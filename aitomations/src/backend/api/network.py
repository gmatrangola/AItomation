"""Network utilities for hostname resolution including mDNS."""

import logging
import socket

from zeroconf import Zeroconf

logger = logging.getLogger(__name__)


def resolve_mdns_hostname(hostname: str, timeout: float = 3.0) -> str | None:
    """
    Resolve a .local mDNS hostname to an IP address using zeroconf.

    Args:
        hostname: The .local hostname to resolve (e.g., 'foil.local')
        timeout: Maximum time to wait for resolution in seconds

    Returns:
        IP address as string, or None if resolution fails

    Raises:
        ValueError: If hostname cannot be resolved with detailed troubleshooting info
    """
    if not hostname.endswith(".local"):
        return None

    logger.info(f"Attempting mDNS resolution for {hostname}")

    zc = None
    try:
        zc = Zeroconf()

        # Remove .local suffix for the query
        name = hostname.replace(".local", "")

        # Query for A record (IPv4)
        info = zc.get_service_info(
            "_workstation._tcp.local.", f"{name}._workstation._tcp.local.", timeout=int(timeout * 1000)
        )

        if info and info.addresses:
            ip = socket.inet_ntoa(info.addresses[0])
            logger.info(f"Resolved {hostname} to {ip} via mDNS")
            return ip

        # Try direct hostname lookup as fallback
        try:
            ip = socket.gethostbyname(hostname)
            logger.info(f"Resolved {hostname} to {ip} via system resolver")
            return ip
        except socket.gaierror:
            pass

    except Exception as e:
        logger.warning(f"mDNS resolution failed for {hostname}: {e}")
        error_msg = (
            f"❌ Cannot resolve mDNS hostname '{hostname}'\n\n"
            f"**Troubleshooting steps:**\n"
            f"1. Ensure the Ollama host is on the same network as Home Assistant\n"
            f"2. Verify mDNS/Bonjour service is running on the Ollama host\n"
            f"3. Check if you can ping `{hostname}` from another device\n"
            f"4. Try using the IP address instead of .local hostname\n"
            f"5. Ensure no firewall is blocking mDNS (UDP port 5353)\n\n"
            f"**Technical details:** {str(e)}"
        )
        raise ValueError(error_msg) from e
    finally:
        if zc:
            zc.close()

    # If we get here, resolution failed
    error_msg = (
        f"❌ Cannot resolve '{hostname}' - host not found on network\n\n"
        f"**Possible causes:**\n"
        f"• The hostname is misspelled\n"
        f"• The Ollama host is not powered on\n"
        f"• The host is not connected to the network\n"
        f"• The host and Home Assistant are on different subnets\n\n"
        f"**Try this:**\n"
        f"• Use the IP address instead (e.g., `http://192.168.1.100:11434`)\n"
        f"• Check your Ollama host configuration"
    )
    raise ValueError(error_msg)


def resolve_hostname(url: str, timeout: float = 3.0) -> str:
    """
    Resolve hostname in URL to IP address, supporting both DNS and mDNS.

    Args:
        url: Full URL (e.g., 'http://foil.local:11434')
        timeout: Maximum time to wait for resolution

    Returns:
        URL with hostname replaced by IP address

    Raises:
        ValueError: If hostname cannot be resolved with troubleshooting guidance
    """
    original_url = url

    # Extract hostname from URL
    hostname_only = url.replace("http://", "").replace("https://", "").split(":")[0].split("/")[0]

    # Check if it's already an IP address
    try:
        socket.inet_aton(hostname_only)
        logger.debug(f"{hostname_only} is already an IP address")
        return original_url
    except OSError:
        pass

    # Try mDNS resolution for .local hostnames
    if hostname_only.endswith(".local"):
        try:
            ip = resolve_mdns_hostname(hostname_only, timeout)
            if ip:
                resolved_url = original_url.replace(hostname_only, ip)
                logger.info(f"Resolved URL: {original_url} -> {resolved_url}")
                return resolved_url
        except ValueError:
            raise

    # Try standard DNS resolution
    try:
        ip = socket.gethostbyname(hostname_only)
        resolved_url = original_url.replace(hostname_only, ip)
        logger.info(f"Resolved {hostname_only} to {ip} via DNS")
        return resolved_url
    except socket.gaierror as e:
        error_msg = (
            f"❌ Cannot resolve hostname '{hostname_only}'\n\n"
            f"**DNS resolution failed.** Please check:\n"
            f"1. The hostname is spelled correctly in your add-on configuration\n"
            f"2. The Ollama host is accessible from Home Assistant's network\n"
            f"3. DNS service is working properly\n"
            f"4. Try using an IP address instead\n\n"
            f"**Current URL:** `{original_url}`\n\n"
            f"**Technical details:** {str(e)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def test_connection(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    Test if a TCP connection can be established to host:port.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        True if connection succeeds, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        success = result == 0
        if success:
            logger.debug(f"Connection test successful for {host}:{port}")
        else:
            logger.warning(f"Connection test failed for {host}:{port} (error code: {result})")
        return success
    except Exception as e:
        logger.warning(f"Connection test failed for {host}:{port}: {e}")
        return False
