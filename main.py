from tkinter import *
from Chessboard import Chessboard


def handle_move(_str):
    pass
    # print("do further evaluation with the position")
    # print(f"Returned position: \n{_str}")


def main():
    root = Tk()
    gui = Chessboard(root, handle_move)
    gui.pack(side="top", fill="both", expand="true", padx=10, pady=10)
    root.mainloop()


if __name__ == "__main__":
    main()
