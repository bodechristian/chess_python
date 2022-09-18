import tkinter as tk
import chess
import chess.pgn
import collections

from datetime import datetime
from PIL import ImageTk, Image


notation_mapper = {
    0: "a",
    1: "b",
    2: "c",
    3: "d",
    4: "e",
    5: "f",
    6: "g",
    7: "h",
}


class Chessboard(tk.Frame):
    SQUARE_SIZE = 80
    pics = {}  # Cache for pictures of pieces

    def __init__(self, parent, handler):
        tk.Frame.__init__(self, parent)

        self.handler = handler
        self.highlighted = None
        self.highlighted_legal_moves = []

        # drag n drop stuff
        self.dragging = False
        self.dragged_obj = None
        self.mouse_x = 0
        self.mouse_y = 0

        self.board = chess.Board()

        self.frame_options = tk.Frame(self)
        self.frame_options.pack(side="left", fill="both", expand="False", anchor="n", padx="5")
        self.lbl_gamestatus = tk.Label(self.frame_options, text="Move 1", bd=15, relief="groove")
        self.lbl_gamestatus.pack(side="top", anchor="n", padx=3, pady=3)
        self.lbl_color_bg = tk.Label(self.frame_options, bg="white", relief="groove")
        self.lbl_color_bg.pack(side="top", anchor="n", fill="x")
        self.lbl_color = tk.Label(self.frame_options, text="White to play", relief="groove")
        self.lbl_color.pack(side="top", anchor="n", fill="x")

        self.lbl_moves = tk.Label(self.frame_options, text="Moves", font=("Arial", 18))
        self.lbl_moves.pack(pady=(15, 0))
        self.frame_moves_wrapper = tk.Frame(self.frame_options)
        self.frame_moves_wrapper.pack(side="top", expand="false", fill="y")
        self.frame_moves_wrapper.grid_columnconfigure(0, weight=1)
        self.frame_moves_wrapper.rowconfigure(0, weight=1)
        self.canvas_moves = tk.Canvas(self.frame_moves_wrapper, width=245)
        self.canvas_moves.grid(row=0, column=0, sticky="new")
        scrollbar = tk.Scrollbar(self.frame_moves_wrapper, orient="vertical", command=self.canvas_moves.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas_moves.configure(yscrollcommand=scrollbar.set)
        self.canvas_moves.bind_all("<MouseWheel>", self.on_mousewheel)

        self.frame_moves = tk.Frame(self.canvas_moves)
        self.canvas_moves.create_window((0, 0), window=self.frame_moves, anchor="nw")

        self.canvas = tk.Canvas(self, width=8*self.SQUARE_SIZE, height=8 * self.SQUARE_SIZE)
        self.canvas.pack(side="top", anchor="c")
        self.canvas.bind("<Button-1>", self.click)

        for i in range(8):
            for j in range(8):
                if (i + j) % 2 == 0:
                    bg_color = "#BEA380"  # light squares
                else:
                    bg_color = "#684A33"  # dark squares
                self.canvas.create_rectangle(i*self.SQUARE_SIZE, j*self.SQUARE_SIZE,
                                             (i+1)*self.SQUARE_SIZE, (j+1)*self.SQUARE_SIZE,
                                             outline="black", fill=bg_color, tags="square")

        self.btn_pgn = tk.Button(self.frame_options, text="Save PGN", command=self.save_pgn)
        self.btn_pgn.pack(side="top")

        self.update_pieces()

    def on_mousewheel(self, event):
        self.canvas_moves.yview_scroll(int(-1*(event.delta/120)), "units")

    @staticmethod
    def to_notation(_row, _col):
        """
        takes row and column and return a string of the chessnotation
        """
        return f"{notation_mapper[_col]}{8-_row}"

    def move(self, cur_row, cur_col):
        # find the move and play it
        _move = self.board.find_move((7 - self.highlighted[0]) * 8 + self.highlighted[1], (7 - cur_row) * 8 + cur_col)

        # update the move sheet
        if self.board.turn:
            lbl_temp_move_nr = tk.Label(self.frame_moves, text=f"{self.board.fullmove_number}.", width=3)
            lbl_temp_move_nr.grid(row=self.board.fullmove_number, column=0, sticky="nesw")
        lbl_temp = tk.Label(self.frame_moves, text=self.board.san(_move), bg="white", bd=1, relief="solid", width=15)
        lbl_temp.grid(row=self.board.fullmove_number, column=(1 - self.board.turn) + 1, sticky="nesw")
        self.frame_moves.update_idletasks()
        self.canvas_moves.config(scrollregion=self.canvas_moves.bbox("all"))
        self.canvas_moves.yview_scroll(100, "units")  # scrolls all the way down

        self.board.push(_move)

        # update visuals
        self.update_pieces()
        self.canvas.delete("highlight")
        self.highlighted = None
        # update options
        self.lbl_color.configure(text=f"{'White to play' if self.board.turn else 'Black to play'}")
        self.lbl_color_bg.configure(bg=f"{'white' if self.board.turn else 'black'}")
        self.frame_options.pack_propagate(0)  # disable resizing after making moves and changing labels
        if outcome := self.board.outcome():
            if outcome.termination == chess.Termination.CHECKMATE:
                if outcome.winner:  # white won
                    self.lbl_gamestatus.configure(text="White wins by Checkmate!")
                else:  # black won
                    self.lbl_gamestatus.configure(text="White wins by Checkmate!")
            # TODO: write something for the other outcomes?
        else:
            self.lbl_gamestatus.configure(text=f"{'Move ' + str(self.board.fullmove_number)}")
        # call handler that a move was made
        self.handler(self.board.__str__())
        return True

    def check_move(self, cur_row, cur_col):
        """
        attempts to make a move from the self.highlighted square to the given square
        :param cur_row: target row
        :param cur_col: target col
        :return: True if the move was successfull, False if not
        """
        if self.highlighted:
            if (cur_row, cur_col) in self.highlighted_legal_moves:
                self.move(cur_row, cur_col)
        return False

    def move_with_string(self, _str):
        str1 = self.board.__str__().replace("\n", "").replace(" ", "")
        str2 = _str.replace("\n", "").replace(" ", "")

        # TODO: catch castling
        zipped = zip(str1, str2)
        if len([1 for c1, c2 in zipped if c1 != c2]) == 2:
            # str1 has to be the previous board! str2 the one with the additional move
            for i, (c1, c2) in enumerate(zip(str1, str2)):
                if c1 != c2:
                    # if there is a difference AND the old position now has no piece there, that means that that's
                    # the origin position
                    if c1 == ".":
                        row2 = i // 8
                        col2 = i % 8
                    else:
                        row1 = i // 8
                        col1 = i % 8
        else:  # castling
            # 2: black long
            # 6: black short
            # 58: white long
            # 62: white short
            for i, (c1, c2) in enumerate(zip(str1, str2)):
                if c1 != c2:
                    if c1.lower() == "k":
                        row1 = i // 8
                        col1 = i % 8
                    if c2.lower() == "k":
                        row2 = i // 8
                        col2 = i % 8

        self.highlighted = (row1, col1)
        self.move(row2, col2)

    def click(self, event):
        cur_row = event.y // self.SQUARE_SIZE
        cur_col = event.x // self.SQUARE_SIZE

        if not self.check_move(cur_row, cur_col):
            self.highlight_square(cur_row, cur_col)

    def highlight_square(self, _row, _col):
        self.canvas.delete("highlight")
        self.canvas.create_rectangle(_col * self.SQUARE_SIZE, _row * self.SQUARE_SIZE,
                                     (_col + 1) * self.SQUARE_SIZE, (_row + 1) * self.SQUARE_SIZE,
                                     outline="black", fill="blue", tags="highlight")
        self.canvas.tag_raise("piece")
        self.highlighted = (_row, _col)

        self.highlighted_legal_moves = []
        for move in self.board.legal_moves:
            if move.from_square == (7-_row)*8+_col:  # chess.Move uses flat idxs from bot-left -> right then up
                self.highlighted_legal_moves.append((7-(move.to_square//8), move.to_square % 8))
        self.highlight_legal_squares(self.highlighted_legal_moves)

    def highlight_legal_squares(self, lst_squares):
        for _row, _col in lst_squares:
            self.canvas.create_oval((_col+0.2)*self.SQUARE_SIZE, (_row+0.2)*self.SQUARE_SIZE, (_col+0.8)*self.SQUARE_SIZE,
                                    (_row+0.8)*self.SQUARE_SIZE, outline=None, fill="grey", tags="highlight")
        self.canvas.tag_raise("piece")

    def update_pieces(self):
        self.canvas.delete("piece")

        # process string
        str_board = self.board.__str__().replace("\n", "").replace(" ", "")

        # go through string and set pieces
        for i, val in enumerate(str_board):
            cur_row = i // 8
            cur_col = i % 8
            str_piece = ""
            if val == ".":
                continue
            if val.isupper():
                str_piece += "white"
            else:
                str_piece += "black"
            str_piece += val.upper()

            if str_piece not in self.pics:
                img = Image.open(f"assets/{str_piece}.png").convert(mode="RGBA")
                self.pics[str_piece] = ImageTk.PhotoImage(img.resize((70, 70)))
            self.canvas.create_image(round((cur_col+0.5)*self.SQUARE_SIZE), round((cur_row+0.5)*self.SQUARE_SIZE),
                                     image=self.pics[str_piece], tags=(str_piece, "piece"), anchor="c")
            self.canvas.tag_bind("piece", "<Button1-Motion>", self.drag)
            self.canvas.tag_bind("piece", "<ButtonRelease-1>", self.drop)

    def drag(self, event):
        if self.dragging:
            self.canvas.move(self.dragged_obj, event.x-self.mouse_x, event.y-self.mouse_y)
            self.mouse_x = event.x
            self.mouse_y = event.y
        else:
            self.dragged_obj = self.canvas.find_closest(event.x, event.y)
            _x, _y = self.canvas.coords(self.dragged_obj)
            self.canvas.move(self.dragged_obj, event.x - _x, event.y - _y)
            self.mouse_x = event.x
            self.mouse_y = event.y
            cur_row = event.y // self.SQUARE_SIZE
            cur_col = event.x // self.SQUARE_SIZE
            self.highlight_square(cur_row, cur_col)
            self.dragging = True

    def drop(self, event):
        self.dragging = False
        cur_row = event.y // self.SQUARE_SIZE
        cur_col = event.x // self.SQUARE_SIZE
        if not self.check_move(cur_row, cur_col):
            self.update_pieces()

    def save_pgn(self):
        game = chess.pgn.Game()

        switchyard = collections.deque()
        while self.board.move_stack:
            switchyard.append(self.board.pop())

        game.setup(self.board)
        node = game

        while switchyard:
            move = switchyard.pop()
            node = node.add_variation(move)
            self.board.push(move)

        game.headers["Result"] = self.board.result()
        game.headers["Date"] = datetime.now().__str__()

        print(game, file=open("pgn_file", "w"), end="\n\n")
        print("saved pgn")

