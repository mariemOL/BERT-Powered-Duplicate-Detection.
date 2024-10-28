import os


os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['MKL_THREADING_LAYER'] = 'sequential'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

from flask import Flask, request, render_template
import torch
from sentence_transformers import SentenceTransformer, util
import mysql.connector



torch.set_num_threads(1)

app = Flask(__name__)


dbconfig = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "opportunet"
}


model = SentenceTransformer('all-MiniLM-L6-v2')

def fetch_opportunities():
    conn = mysql.connector.connect(**dbconfig)
    cursor = conn.cursor()
    cursor.execute("SELECT client, titre, details, budget FROM opportunities")
    rows = cursor.fetchall()
    conn.close()
    return rows

def prepare_text_data(rows):
    return [f"{row[1]} {row[2]}" for row in rows]  #

def compute_similarity(target_sentence, texts):

    embeddings = model.encode([target_sentence] + texts, convert_to_tensor=True)
    
    
    cosine_scores = util.pytorch_cos_sim(embeddings[0], embeddings[1:])
    return cosine_scores[0]


@app.route('/')
def index():
    return render_template('form.html')  

@app.route('/compare', methods=['POST'])
def compare():
    client = request.form['client']
    titre = request.form['titre']
    details = request.form['details']
    budget = float(request.form['budget'])  
    target_sentence = f"{titre} {details}"

    
    rows = fetch_opportunities()
    texts = prepare_text_data(rows)
    

    cosine_scores = compute_similarity(target_sentence, texts)

    similarity_threshold = 0.7
    budget_tolerance = 0.1  

    results = []
    is_duplicate = False  
    for idx, score in enumerate(cosine_scores):
        db_client = rows[idx][0]
        db_budget = rows[idx][3]

        if db_client == client and abs(db_budget - budget) / db_budget <= budget_tolerance:
            if score >= similarity_threshold:
                is_duplicate = True  
                results.append({
                    'entry': texts[idx],
                    'score': score.item(),
                    'client': db_client,
                    'budget': db_budget,
                    'duplicate_message': "C'est peut-être un doublon"  
                })


    results = sorted(results, key=lambda x: x['score'], reverse=True)

    return render_template('results.html', results=results, target_sentence=target_sentence, is_duplicate=is_duplicate)

if __name__ == '__main__':
    app.run(debug=True)

