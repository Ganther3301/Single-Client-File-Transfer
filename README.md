# File Transfer System

A Python client-server file transfer system with chunking and error recovery.

## Usage

1. **Start the application:**

   ```bash
   python main.py
   ```

2. **Start the server** (choose option 1 or 2):

   - Option 1: Normal mode
   - Option 2: With error simulation

3. **Transfer a file** (option 3 in a new terminal):

   - Run `python main.py` again
   - Choose option 3
   - Enter the file path to transfer

4. **Create test files** (option 4):
   - Generate sample files for testing

## Menu Options

- **1** - Start Server
- **2** - Start Server (with error simulation)
- **3** - Transfer File (Client)
- **4** - Create Test File
- **5** - Exit

## Example

```bash
# Terminal 1: Start server
python main.py
# Choose option 1

# Terminal 2: Transfer file
python main.py
# Choose option 3
# Enter: test_data.txt
```

The transferred file will be saved as `received_[filename]` in the client directory.
