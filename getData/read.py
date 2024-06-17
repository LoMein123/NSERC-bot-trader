"""
This module serves as an example of how to decode the binary files generated by intraday.py
"""
import struct

#Dictionaires for converting call/put and bid/ask to 0 and 1
cp = {0: "C", 1: "P"}
ba = {0: "B", 1: "A"}

def read_data_from_binary(file_path: str) -> list:
    """
    Function that reads data from the given file path and converts it to a list. 
    Note that 0/1 = Call/Put and 0/1 = Bid/Ask.

    Parameters
    ----------
    file_path: File path

    Returns
    ----------
    list of values in file_path where each row is [timestamp, strike price, right, bid, ask]
    """
    data_list: list = []

    struct_format: str = 'iiifi'                        # Each struct (line) is [int, int, int, float, int]
    struct_size: int = struct.calcsize(struct_format)   # Calculate bytes per struct

    with open(file_path, 'rb') as f:
        while True:
            # Read a chunk of bytes corresponding to the bytes per struct
            bytes_chunk = f.read(struct_size)
            if not bytes_chunk:
                break

            # Unpack the bytes chunk
            unpacked_data = struct.unpack(struct_format, bytes_chunk)
            data_list.append(unpacked_data)
    
    return data_list


def main() -> None:
    # Read the data from the binary file
    file_path: str = 'intraday.bin'
    data: list = read_data_from_binary(file_path)

    # Print the data
    for line in data:
        time, right, side, bidAskPrice, strike = line
        print(f"Timestamp: {time}, Call/Put: {cp[right]}, Bid/Ask: {ba[side]}, Bid/Ask Price: {bidAskPrice:.2f}, Strike Price: {strike}")


if __name__ == "__main__":
    main()