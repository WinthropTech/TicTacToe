from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import math

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Global game state
game_board = [""] * 9
game_over = False
winner = None

# History for undo functionality (stores previous game states)
history = []

def save_state():
    """Save the current state for potential undo."""
    global history, game_board, game_over, winner
    state = {
         "board": game_board.copy(),
         "game_over": game_over,
         "winner": winner
    }
    history.append(state)

def undo_state():
    """Undo the last move, if available."""
    global history, game_board, game_over, winner
    if history:
         state = history.pop()
         game_board[:] = state["board"]
         game_over = state["game_over"]
         winner = state["winner"]
         return True
    else:
         return False

def is_winner(board, player):
    win_conditions = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]
    for condition in win_conditions:
        if all(board[i] == player for i in condition):
            return True
    return False

def is_draw(board):
    return all(cell != "" for cell in board)

def minimax(board, is_maximizing, alpha=-math.inf, beta=math.inf):
    # Terminal state evaluation
    if is_winner(board, "O"):
        return 1
    elif is_winner(board, "X"):
        return -1
    elif is_draw(board):
        return 0

    if is_maximizing:
        best_score = -math.inf
        for i in range(9):
            if board[i] == "":
                board[i] = "O"
                score = minimax(board, False, alpha, beta)
                board[i] = ""
                best_score = max(best_score, score)
                alpha = max(alpha, best_score)
                if beta <= alpha:
                    break  # Beta cut-off
        return best_score
    else:
        best_score = math.inf
        for i in range(9):
            if board[i] == "":
                board[i] = "X"
                score = minimax(board, True, alpha, beta)
                board[i] = ""
                best_score = min(best_score, score)
                beta = min(beta, best_score)
                if beta <= alpha:
                    break  # Alpha cut-off
        return best_score

def best_move(board):
    best_score = -math.inf
    move = None
    for i in range(9):
        if board[i] == "":
            board[i] = "O"
            score = minimax(board, False)
            board[i] = ""
            if score > best_score:
                best_score = score
                move = i
    return move

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "board": game_board})

@app.post("/move")
async def make_move(data: dict):
    global game_board, game_over, winner
    position = data.get("position")
    
    if game_over:
        return JSONResponse({
            "error": "Game over. Please reset the game.",
            "board": game_board
        })
    if game_board[position] != "":
        return JSONResponse({
            "error": "Invalid move",
            "board": game_board
        })
    
    # Save state for undo before the human move.
    save_state()
    
    # Human move ("X")
    game_board[position] = "X"
    
    # Check if human wins
    if is_winner(game_board, "X"):
        game_over = True
        winner = "X"
        return JSONResponse({
            "board": game_board,
            "status": "human_win"
        })
    
    # Check for draw after human move
    if is_draw(game_board):
        game_over = True
        return JSONResponse({
            "board": game_board,
            "status": "draw"
        })
    
    # AI move ("O")
    ai_move = best_move(game_board)
    if ai_move is not None:
        game_board[ai_move] = "O"
    
    # Check if AI wins
    if is_winner(game_board, "O"):
        game_over = True
        winner = "O"
        return JSONResponse({
            "board": game_board,
            "status": "ai_win"
        })
    
    # Check for draw after AI move
    if is_draw(game_board):
        game_over = True
        return JSONResponse({
            "board": game_board,
            "status": "draw"
        })
    
    return JSONResponse({
        "board": game_board,
        "status": "ongoing"
    })

@app.post("/reset")
async def reset_game(data: dict = None):
    global game_board, game_over, winner, history
    game_board = [""] * 9
    game_over = False
    winner = None
    history = []  # clear undo history on reset
    
    # Default to human first if no data provided.
    first = "human"
    if data is not None and "first" in data:
        first = data["first"]

    # If AI goes first, make its move immediately.
    if first == "ai":
        ai_move = best_move(game_board)
        if ai_move is not None:
            game_board[ai_move] = "O"
    
    return JSONResponse({
        "board": game_board,
        "status": "reset",
        "first": first
    })

@app.post("/undo")
async def undo():
    # Only allow one level of undo. After undoing, clear the history.
    if undo_state():
        history.clear()
        return JSONResponse({
            "board": game_board,
            "status": "undo_success"
        })
    else:
        return JSONResponse({
            "error": "No moves to undo",
            "board": game_board
        })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
