import sys
import pickle
import socket
import socketserver
import struct
import threading
from PyQt5.QtWidgets import QMessageBox



class RequestHandler(socketserver.StreamRequestHandler):
    AskLock = threading.Lock()

    call = dict(ASK=(
        lambda self, *args: self.asked_question(*args)))

    def handle(self):
        size_struct = struct.Struct("!I")
        size_data = self.rfile.read(size_struct.size)
        size = size_struct.unpack(size_data)[0]
        data = pickle.loads(self.rfile.read(size))
        cur_thread = threading.current_thread()
        try:
            print("received data: {} ".format(data))
            with RequestHandler.AskLock:
                function = self.call[data[0]]
            reply = function(self, *data[1:])
            print(data[1:])
        except Finish:
            return
        data = pickle.dumps((reply, 4))
        self.wfile.write(size_struct.pack(len(data)))
        self.wfile.write(data)

    def handle_request(self, address, *items, wait_for_reply=True):
        SizeStruct = struct.Struct("!I")
        data = pickle.dumps(items[0], 4)

        try:
            with SocketManager(tuple(address)) as sock:
                sock.sendall(SizeStruct.pack(len(data)))
                sock.sendall(data)
                if not wait_for_reply:
                    return
                size_data = sock.recv(SizeStruct.size)
                size = SizeStruct.unpack(size_data)[0]
                result = bytearray()
                while True:
                    data = sock.recv(4000)
                    if not data:
                        break
                    result.extend(data)
                    if len(result) >= size:
                        break
            return pickle.loads(result)
        except socket.error as err:
            print(err)
        except Exception as arr:
            message = "Is the server running? {}".format(arr)
            popup = QMessageBox()
            popup.setText("The server connection failed")
            popup.setDetailedText(message)
            popup.Critical
            popup.exec_()

    def check_db(self,*items):
        args, address = items
        ok, data = self.handle_request(address, ["CHECK_DB"])
        print(ok)
        return ok


class SocketManager:

    def __init__(self, address):
        self.address = address

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.address)
        return self.sock

    def __exit__(self,*ignore):
        self.sock.close()

class Finish(Exception): pass

class ClientAnswerServer(socketserver.ThreadingTCPServer,socketserver.TCPServer):
    try:
        def __init__(self, server_address, RequestHandlerClass):
            socketserver.ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass)
    except Exception as err:
        print(err)

if __name__ == '__main__':
    address_ = 'SERVER', 9000
    con = RequestHandler.handle_request(" ", address_, ['TEST_DB'])
