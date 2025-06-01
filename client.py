import socket
import json
import hashlib
import struct
import os
import time

CHUNK_SIZE = 1024
BUFFER_SIZE = 4096
SERVER_HOST = "localhost"
SERVER_PORT = 8888
TIMEOUT = 30
MAX_RETRIES = 3


class FileTransferClient:
    """Client class for sending files and receiving chunked data."""

    def __init__(self, server_host: str = SERVER_HOST, server_port: int = SERVER_PORT):
        self.server_host = server_host
        self.server_port = server_port

    def transfer_file(self, file_path: str) -> bool:
        """Transfer a file to the server and receive it back in chunks."""
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found")
            return False

        try:
            # Connect to server
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(TIMEOUT)
            client_socket.connect((self.server_host, self.server_port))

            print(f"Connected to server {self.server_host}:{self.server_port}")

            # Send file to server
            if not self.send_file(client_socket, file_path):
                return False

            # Receive processed file back
            success = self.receive_chunked_file(client_socket, file_path)

            client_socket.close()
            return success

        except socket.timeout:
            print("Error: Connection timed out")
            return False
        except ConnectionRefusedError:
            print("Error: Could not connect to server")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    def send_file(self, client_socket: socket.socket, file_path: str) -> bool:
        """Send file to server."""
        try:
            filename = os.path.basename(file_path)

            with open(file_path, "rb") as f:
                file_data = f.read()

            # Send metadata
            metadata = {"filename": filename, "file_size": len(file_data)}

            metadata_json = json.dumps(metadata).encode("utf-8")
            metadata_length = struct.pack("!I", len(metadata_json))
            client_socket.send(metadata_length + metadata_json)

            # Send file data
            bytes_sent = 0
            while bytes_sent < len(file_data):
                chunk = file_data[bytes_sent : bytes_sent + BUFFER_SIZE]
                sent = client_socket.send(chunk)
                bytes_sent += sent

            print(f"Sent file '{filename}' ({len(file_data)} bytes)")
            return True

        except Exception as e:
            print(f"Error sending file: {e}")
            return False

    def receive_chunked_file(
        self, client_socket: socket.socket, original_file_path: str
    ) -> bool:
        """Receive file back in chunks and verify integrity."""
        try:
            # Receive transfer metadata
            transfer_info = self.receive_json(client_socket)
            if not transfer_info:
                return False

            filename = transfer_info["filename"]
            total_chunks = transfer_info["total_chunks"]
            expected_checksum = transfer_info["checksum"]
            file_size = transfer_info["file_size"]

            print(f"Receiving '{filename}' in {total_chunks} chunks")
            print(f"Expected checksum: {expected_checksum}")

            # Receive chunks with retry logic
            chunks = self.receive_chunks_with_retry(client_socket, total_chunks)

            if len(chunks) != total_chunks:
                print(
                    f"Error: Missing chunks. Expected {total_chunks}, got {len(chunks)}"
                )
                return False

            # Reassemble file
            reassembled_data = self.reassemble_chunks(chunks, total_chunks)

            # Verify checksum
            calculated_checksum = hashlib.sha256(reassembled_data).hexdigest()

            if calculated_checksum == expected_checksum:
                print("✓ Transfer Successful - Checksum verified!")

                # Save reassembled file
                output_path = f"received_{filename}"
                with open(output_path, "wb") as f:
                    f.write(reassembled_data)
                print(f"File saved as '{output_path}'")

                return True
            else:
                print("✗ Transfer Failed - Checksum mismatch!")
                print(f"Expected: {expected_checksum}")
                print(f"Calculated: {calculated_checksum}")
                return False

        except Exception as e:
            print(f"Error receiving chunked file: {e}")
            return False

    def receive_chunks_with_retry(
        self, client_socket: socket.socket, total_chunks: int
    ) -> dict[int, bytes]:
        """Receive chunks with retry logic for missing/corrupted chunks."""
        chunks = {}
        missing_chunks = set()
        retry_count = 0

        while retry_count < MAX_RETRIES:
            # Receive available chunks
            while True:
                try:
                    chunk_packet = self.receive_json(client_socket)
                    if not chunk_packet:
                        break

                    seq_num = chunk_packet["seq_num"]

                    # End of transmission marker
                    if seq_num == -1:
                        break

                    chunk_data = bytes.fromhex(chunk_packet["data"])

                    # Verify chunk integrity (simple size check)
                    if len(chunk_data) == chunk_packet["size"]:
                        chunks[seq_num] = chunk_data
                        if seq_num in missing_chunks:
                            missing_chunks.remove(seq_num)
                    else:
                        print(f"Corrupted chunk {seq_num} detected")
                        missing_chunks.add(seq_num)

                except Exception as e:
                    print(f"Error receiving chunk: {e}")
                    break

            # Check for missing chunks
            received_seq_nums = set(chunks.keys())
            expected_seq_nums = set(range(total_chunks))
            missing_chunks.update(expected_seq_nums - received_seq_nums)

            if not missing_chunks:
                break

            print(
                f"Missing chunks: {sorted(missing_chunks)} (Retry {retry_count + 1}/{MAX_RETRIES})"
            )
            retry_count += 1

            if retry_count < MAX_RETRIES:
                # Request retransmission (in a real implementation)
                time.sleep(1)  # Wait before retry

        return chunks

    def reassemble_chunks(self, chunks: dict[int, bytes], total_chunks: int) -> bytes:
        """Reassemble chunks in correct order."""
        reassembled_data = b""

        for seq_num in range(total_chunks):
            if seq_num in chunks:
                reassembled_data += chunks[seq_num]
            else:
                raise Exception(f"Missing chunk {seq_num}")

        return reassembled_data

    def receive_json(self, client_socket: socket.socket):
        """Receive JSON data with length prefix."""
        try:
            # Receive length
            length_data = client_socket.recv(4)
            if len(length_data) != 4:
                return None

            length = struct.unpack("!I", length_data)[0]

            # Receive JSON data
            json_data = b""
            while len(json_data) < length:
                chunk = client_socket.recv(length - len(json_data))
                if not chunk:
                    return None
                json_data += chunk

            return json.loads(json_data.decode("utf-8"))

        except Exception as e:
            print(f"Error receiving JSON: {e}")
            return None
