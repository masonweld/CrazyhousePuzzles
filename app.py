from flask import Flask, render_template, request, jsonify
import chess.variant
import random
import json
import os

app = Flask(__name__)

MASTER_JSON_FILE = 'static/data/master_puzzles.json'

FALLBACKS = {
    1: { "fen": "r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1[N] w kq - 0 1", "solution": ["N@f7"], "url": "https://lichess.org", "white": "Player1", "black": "Player2" },
    2: { "fen": "5rk1/5ppp/7Q/8/8/8/8/6RK[N] w - - 0 1", "solution": ["N@f6", "g8h8", "h6h7"], "url": "https://lichess.org", "white": "Player1", "black": "Player2" },
    3: { "fen": "r1bqk2r/pppp1ppp/2n5/4p3/2B1n3/5N2/PPPP1PPP/RNBQ1RK1[NN] w kq - 0 1", "solution": ["N@f7", "Kf8", "N@d7", "Kg8", "N@h6"], "url": "https://lichess.org", "white": "Player1", "black": "Player2" }
}

PUZZLES_BY_MATE = {1: [], 2: [], 3: []}
ALL_PUZZLES = [] # NEW: Flat list for fast username searching

def load_master_puzzles():
    if os.path.exists(MASTER_JSON_FILE):
        with open(MASTER_JSON_FILE, 'r', encoding='utf-8') as f:
            try:
                all_puzzles = json.load(f)
                for p in all_puzzles:
                    mate = p.get('mate_in', 1) 
                    if mate in PUZZLES_BY_MATE:
                        PUZZLES_BY_MATE[mate].append(p)
                    ALL_PUZZLES.append(p) # Add to the flat list
                print(f"Successfully loaded {len(ALL_PUZZLES)} puzzles into memory.")
            except json.JSONDecodeError:
                print(f"Warning: {MASTER_JSON_FILE} is invalid or corrupted.")

load_master_puzzles()

@app.route('/')
def index():
    puzzle_list = PUZZLES_BY_MATE[1]
    puzzle = random.choice(puzzle_list) if puzzle_list else FALLBACKS[1]
    
    solution = puzzle['solution'] if isinstance(puzzle['solution'], list) else [puzzle['solution']]
    url = puzzle.get('url', 'https://lichess.org')
    
    return render_template('index.html', fen=puzzle['fen'], solution=solution, url=url)

@app.route('/get_puzzle', methods=['GET'])
def get_puzzle():
    username = request.args.get('username', '').strip().lower()
    
    # NEW: Username search logic
    if username:
        user_puzzles = [p for p in ALL_PUZZLES if p.get('white', '').lower() == username or p.get('black', '').lower() == username]
        
        if not user_puzzles:
            return jsonify({'error': f'No puzzles found for user: {username}'})
            
        puzzle = random.choice(user_puzzles)
        
    # Normal difficulty mode
    else:
        mate_type = int(request.args.get('mate', 1))
        if mate_type not in PUZZLES_BY_MATE:
            mate_type = 1
            
        puzzle_list = PUZZLES_BY_MATE[mate_type]
        puzzle = random.choice(puzzle_list) if puzzle_list else FALLBACKS[mate_type]
        
    solution = puzzle['solution'] if isinstance(puzzle['solution'], list) else [puzzle['solution']]
    
    # Send all the rich metadata to the frontend
    return jsonify({
        'fen': puzzle['fen'], 
        'solution': solution, 
        'url': puzzle.get('url', 'https://lichess.org'),
        'white': puzzle.get('white', '?'),
        'black': puzzle.get('black', '?'),
        'white_elo': puzzle.get('white_elo', '?'),
        'black_elo': puzzle.get('black_elo', '?')
    })

@app.route('/validate_move', methods=['POST'])
def validate_move():
    data = request.json
    current_fen = data.get('fen')
    move_uci = data.get('move')
    board = chess.variant.CrazyhouseBoard(current_fen)
    
    try:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)
            return jsonify({'valid': True, 'new_fen': board.fen(), 'is_mate': board.is_checkmate()})
        else:
            return jsonify({'valid': False, 'error': 'Illegal move'})
    except ValueError:
        return jsonify({'valid': False, 'error': 'Invalid move format'})

if __name__ == '__main__':
    app.run(debug=True)