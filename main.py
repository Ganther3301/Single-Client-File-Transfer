from client import FileTransferClient
from server import Server


def create_test_file(filename: str, size_kb: int = 10):
    """Create a test file for demonstration."""
    content = "Hello, this is a test file for the file transfer system!\n" * (
        size_kb * 1024 // 60
    )

    with open(filename, "w") as f:
        f.write(content[: size_kb * 1024])

    print(f"Created test file '{filename}' ({size_kb} KB)")


if __name__ == "__main__":
    """Main function with menu-driven interface."""
    print("Real-Time File Transfer System")
    print("=" * 40)

    while True:
        print("\nOptions:")
        print("1. Start Server")
        print("2. Start Server (with error simulation)")
        print("3. Transfer File (Client)")
        print("4. Create Test File")
        print("5. Exit")

        try:
            choice = input("\nEnter your choice (1-5): ").strip()

            if choice == "1":
                server = Server()
                try:
                    server.start(simulation_errors=False)
                except KeyboardInterrupt:
                    pass

            elif choice == "2":
                server = Server()
                try:
                    server.start(simulation_errors=True)
                except KeyboardInterrupt:
                    pass

            elif choice == "3":
                file_path = input("Enter file path to transfer: ").strip()
                if file_path:
                    client = FileTransferClient()
                    success = client.transfer_file(file_path)
                    if success:
                        print("File transfer completed successfully!")
                    else:
                        print("File transfer failed!")

            elif choice == "4":
                filename = input("Enter filename (default: test_data.txt): ").strip()
                if not filename:
                    filename = "test_data.txt"

                try:
                    size = int(
                        input("Enter file size in KB (default: 10): ").strip() or "10"
                    )
                    create_test_file(filename, size)
                except ValueError:
                    create_test_file(filename, 10)

            elif choice == "5":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("Goodbye!")
            break
