import socket

import threading
import hashlib
import json

import time
import random
import struct


CHUNK_SIZE = 1024
BUFFER_SIZE = 4096
SERVER_HOST = "localhost"
SERVER_PORT = 8888
TIMEOUT = 30
MAX_RETRIES = 3


class Server:
    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.simulate_errors = False
        self.packet_loss = 0.5

    def start(self, simulation_errors=False):
        self.simulate_errors = simulation_errors
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            print(f"Server listening on {self.host}:{self.port}")
            print(f"Error simulation: {'ON' if simulation_errors else 'OFF'}")

            while True:
                client_socket, addr = self.socket.accept()
                print(f"Connection from {addr}")

                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()

        except KeyboardInterrupt:
            print("\nServer shutting down...")
        except OSError as e:
            print(e)
        finally:
            if self.socket:
                self.socket.close()

    def handle_client(self, client_socket: socket.socket, addr: tuple):
        """Handle individual client connections."""
        try:
            # Receive file from client
            file_data = self.receive_file(client_socket)
            if not file_data:
                return

            filename, data = file_data
            print(f"Received file '{filename}' ({len(data)} bytes) from {addr}")

            # Process and send back the file in chunks
            self.process_and_send_file(client_socket, filename, data)

        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            client_socket.close()

    def receive_file(self, client_socket: socket.socket):
        """Receive file from client."""
        try:
            # Receive metadata (filename and file size)
            metadata_size = struct.unpack("!I", client_socket.recv(4))[0]
            metadata_json = client_socket.recv(metadata_size).decode("utf-8")
            metadata = json.loads(metadata_json)
            print(metadata)

            filename = metadata["filename"]
            file_size = metadata["file_size"]

            # Receive file data
            file_data = b""
            bytes_received = 0

            while bytes_received < file_size:
                chunk = client_socket.recv(min(BUFFER_SIZE, file_size - bytes_received))
                if not chunk:
                    break
                file_data += chunk
                bytes_received += len(chunk)

            if bytes_received != file_size:
                raise Exception(
                    f"File size mismatch: expected {file_size}, got {bytes_received}"
                )

            return filename, file_data

        except Exception as e:
            print(f"Error receiving file: {e}")
            return None

    def process_and_send_file(
        self, client_socket: socket.socket, filename: str, data: bytes
    ):
        """Split file into chunks and send with checksum."""
        try:
            # Calculate checksum
            checksum = hashlib.sha256(data).hexdigest()
            print(f"File checksum: {checksum}")

            # Split into chunks
            chunks = self.split_into_chunks(data)
            total_chunks = len(chunks)

            print(f"Split file into {total_chunks} chunks")

            # Send transfer metadata
            transfer_info = {
                "filename": filename,
                "total_chunks": total_chunks,
                "chunk_size": CHUNK_SIZE,
                "checksum": checksum,
                "file_size": len(data),
            }

            self.send_json(client_socket, transfer_info)

            # Send chunks with sequence numbers
            self.send_chunks(client_socket, chunks)

        except Exception as e:
            print(f"Error processing file: {e}")

    def split_into_chunks(self, data: bytes) -> list[bytes]:
        """Split data into fixed-size chunks."""
        chunks = []
        for i in range(0, len(data), CHUNK_SIZE):
            chunks.append(data[i : i + CHUNK_SIZE])
        return chunks

    def send_chunks(self, client_socket: socket.socket, chunks: list[bytes]):
        """Send chunks with sequence numbers and error simulation."""
        for seq_num, chunk in enumerate(chunks):
            try:
                # Simulate packet loss/corruption
                if self.simulate_errors and random.random() < self.packet_loss:
                    if random.choice([True, False]):  # 50% loss, 50% corruption
                        print(f"Simulating packet loss for chunk {seq_num}")
                        continue  # Skip sending this chunk
                    else:
                        print(f"Simulating packet corruption for chunk {seq_num}")
                        chunk = self.corrupt_data(chunk)

                # Create chunk packet
                chunk_packet = {
                    "seq_num": seq_num,
                    "data": chunk.hex(),  # Convert to hex for JSON serialization
                    "size": len(chunk),
                }

                self.send_json(client_socket, chunk_packet)
                time.sleep(0.01)  # Small delay to simulate network latency

            except Exception as e:
                print(f"Error sending chunk {seq_num}: {e}")
                break

        # Send end-of-transmission marker
        end_packet = {"seq_num": -1, "data": "", "size": 0}
        self.send_json(client_socket, end_packet)

    def corrupt_data(self, data: bytes) -> bytes:
        """Simulate data corruption by flipping random bits."""
        if len(data) == 0:
            return data

        data_array = bytearray(data)
        # Corrupt 1-3 random bytes
        for _ in range(random.randint(1, min(3, len(data_array)))):
            pos = random.randint(0, len(data_array) - 1)
            data_array[pos] ^= random.randint(1, 255)

        return bytes(data_array)

    def send_json(self, client_socket: socket.socket, data: dict):
        """Send JSON data with length prefix."""
        json_data = json.dumps(data).encode("utf-8")
        length = struct.pack("!I", len(json_data))
        client_socket.send(length + json_data)


if __name__ == "__main__":
    server = Server()
    server.start()
