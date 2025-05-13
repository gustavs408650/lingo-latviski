from flask import Flask, render_template, request, redirect, url_for, session, flash
import random
import logging
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'lingo_secret_key'  # Required for session

# Set up logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    filename=f'logs/lingo_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Sample words (variable lengths)
WORDS = [
    'KĀRLIS', 'GRIETA', 'VITA', 'GUSTAVS', 'TĒTIS', 'MAMMA', 'BRĀLIS', 'MĀSA', 'LAPSAS', 'ZAĶI'
]

def init_game(reset_lives=False, reset_score=False):
    """Initialize or reset game state. If reset_lives is True, set lives to 5. If reset_score is True, set score to 0."""
    word = random.choice(WORDS)
    session['current_word'] = word
    session['word_length'] = len(word)
    session['current_row'] = 0
    if reset_lives or 'lives' not in session:
        session['lives'] = 5
    if reset_score or 'score' not in session:
        session['score'] = 0
    if reset_score or 'words_guessed' not in session:
        session['words_guessed'] = 0
    session['guesses'] = []
    session['used_letters'] = []  # Store as list, not set
    session.pop('game_over', None)
    session.pop('game_over_word', None)
    session.pop('game_over_score', None)
    session.pop('game_over_words_guessed', None)
    logging.info(f"New game started. Word: {session['current_word']}")

@app.route('/')
def home():
    """Render the game page"""
    if 'current_word' not in session:
        init_game(reset_lives=True, reset_score=True)
    return render_template('index.html')

@app.route('/guess', methods=['POST'])
def make_guess():
    """Process a guess"""
    guess = request.form.get('guess', '').upper()
    word_length = session['word_length']
    
    # Stricter check: must be exactly word_length letters, all alphabetic
    if len(guess) != word_length or not guess.isalpha():
        flash(f'Lūdzu ievadiet tieši {word_length} burtus!')
        logging.info(f"Invalid guess attempted: {guess}")
        return redirect(url_for('home'))
    
    current_word = session['current_word']
    # SAFETY: If current_word is not word_length letters, re-init game
    if len(current_word) != word_length:
        flash('Kļūda ar vārdu. Sākam jaunu spēli!')
        logging.error(f"Invalid word length in session: {current_word}")
        init_game()
        return redirect(url_for('home'))
    
    current_row = session['current_row']
    lives = session['lives']
    score = session['score']
    words_guessed = session.get('words_guessed', 0)
    guesses = session.get('guesses', [])
    used_letters = set(session.get('used_letters', []))  # Convert to set for logic
    
    # Log the guess
    logging.info(f"Guess #{current_row + 1}: {guess} (Word: {current_word})")
    
    # --- Improved Lingo/Wordle-style evaluation ---
    answer = list(current_word)
    guess_letters = list(guess)
    result = [None] * word_length
    answer_used = [False] * word_length

    # First pass: mark greens
    for i in range(word_length):
        if guess_letters[i] == answer[i]:
            result[i] = {'letter': guess_letters[i], 'status': 'correct'}
            answer_used[i] = True
        
    # Second pass: mark yellows and grays
    for i in range(word_length):
        if result[i] is not None:
            continue
        found = False
        for j in range(word_length):
            if not answer_used[j] and guess_letters[i] == answer[j]:
                found = True
                answer_used[j] = True
                break
        if found:
            result[i] = {'letter': guess_letters[i], 'status': 'wrong-position'}
        else:
            result[i] = {'letter': guess_letters[i], 'status': 'incorrect'}
            used_letters.add(guess_letters[i])
    # --- End improved evaluation ---

    # Log the result
    logging.info(f"Result: {result}")
    
    # Update game state
    guesses.append(result)
    session['guesses'] = guesses
    session['current_row'] = current_row + 1
    session['used_letters'] = list(used_letters)  # Store as list
    
    # Check win condition
    if guess == current_word:
        score += (word_length - current_row) * 100
        session['score'] = score
        session['won'] = True
        session['words_guessed'] = words_guessed + 1
        logging.info(f"Game won! Score: {score}")
        flash('Apsveicam! Jūs uzvarējāt!')
        return redirect(url_for('home'))
    
    # Check lose condition
    if current_row + 1 >= 5:
        lives -= 1
        session['lives'] = lives
        
        if lives <= 0:
            logging.info(f"Game lost! Word was: {current_word}")
            session['game_over'] = True
            session['game_over_word'] = current_word
            session['game_over_score'] = score
            session['game_over_words_guessed'] = words_guessed
            flash(f'Spēle beigusies! Pareizais vārds bija: {current_word}')
            return redirect(url_for('home'))
        else:
            logging.info(f"Round lost. Lives remaining: {lives}")
            session['lost_word'] = True
            session['lost_word_answer'] = current_word
            flash(f'Jūs zaudējāt vienu dzīvību! Pareizais vārds bija: {current_word}')
            # Do NOT start new word yet
        return redirect(url_for('home'))
    
    return redirect(url_for('home'))

@app.route('/next-game')
def next_game():
    """Start a new word after a win or lost word"""
    session.pop('won', None)
    session.pop('lost_word', None)
    session.pop('lost_word_answer', None)
    init_game(reset_lives=False, reset_score=False)
    return redirect(url_for('home'))

@app.route('/new-game')
def new_game():
    """Start a new game (reset everything)"""
    logging.info("Manual new game started")
    init_game(reset_lives=True, reset_score=True)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True) 