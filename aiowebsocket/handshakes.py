import re
import random
import base64

from .exceptions import HandShakeError


_value_re = re.compile(rb"[\x09\x20-\x7e\x80-\xff]*")


class HandShake:
    """This section is non-normative.
    The opening handshake is intended to be compatible with HTTP-based
    server-side software and intermediaries, so that a single port can be
    used by both HTTP clients talking to that server and WebSocket
    clients talking to that server.  To this end, the WebSocket client's
    handshake is an HTTP Upgrade request

    https://tools.ietf.org/html/rfc6455#section-1.3
    """
    def __init__(self, remote, reader, writer, headers):
        self.remote = remote
        self.write = writer
        self.reader = reader
        self.headers = headers

    @staticmethod
    def shake_headers(host: str, port: int, resource: str = '/',
                      version: int = 13, headers: list = []):
        """Request header information for handshaking
        In compliance with [RFC2616], header fields in the handshake may be
        sent by the client in any order, so the order in which different
        header fields are received is not significant.
        """
        if headers:
            # Allow the use of custom header
            return '\r\n'.join(headers) + '\r\n'

        bytes_key = bytes(random.getrandbits(8) for _ in range(16))
        key = base64.b64encode(bytes_key).decode()
        headers = ['GET {resource} HTTP/1.1'.format(resource=resource),
                   'Host: {host}:{port}'.format(host=host, port=port),
                   'Upgrade: websocket',
                   'Connection: Upgrade',
                   'User-Agent: Python/3.7',
                   'Sec-WebSocket-Key: {key}'.format(key=key),
                   'Origin: {host}'.format(host=host),
                   'Sec-WebSocket-Version: {version}'.format(version=version),
                   '\r\n']
        return '\r\n'.join(headers)

    async def shake_(self):
        """Initiate a handshake"""
        porn, host, port, resource, users = self.remote
        handshake_info = self.shake_headers(host=host, port=port,
                                            resource=resource, headers=self.headers)
        self.write.write(data=handshake_info.encode())

    async def shake_result(self):
        """Check handshake results
        Any status code other than 101 indicates that the WebSocket handshake
        has not completed and that the semantics of HTTP still apply.  The
        headers follow the status code.
        """
        header = []
        for _ in range(2**8):
            result = await self.reader.readline()
            header.append(result)
            if result == b'\r\n':
                break
        if not header:
            raise HandShakeError('HandShake not response')
        protocols, socket_code = header[0].decode('utf-8').split()[:2]
        if protocols != "HTTP/1.1":
            raise HandShakeError("Unsupported HTTP version: %r" % protocols)
        socket_code = int(socket_code)
        if not 100 <= socket_code < 1000:
            raise HandShakeError("Unsupported HTTP status code: %d" % socket_code)
        return socket_code

