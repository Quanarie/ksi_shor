import matplotlib
matplotlib.use('Agg')

from flask import Flask, render_template, request, jsonify
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFTGate
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
from fractions import Fraction
from math import gcd
import os
import uuid
import time

app = Flask(__name__)

def c_amod15(a, power):
    if a not in [2, 4, 7, 8, 11, 13]:
        raise ValueError("a must be one of: 2,4,7,8,11,13")
    U = QuantumCircuit(4)
    for _ in range(power):
        if a in [2, 13]: U.swap(0, 1); U.swap(1, 2); U.swap(2, 3)
        if a in [7, 8]: U.swap(2, 3); U.swap(1, 2); U.swap(0, 1)
        if a in [4, 11]: U.swap(0, 2); U.swap(1, 3)
        if a in [7, 11, 13]:
            for q in range(4): U.x(q)
    U = U.to_gate()
    U.name = f"{a}^{power} mod 15"
    return U.control()

def shor_circuit(a, n_count=8):
    qcircuit = QuantumCircuit(n_count + 4, n_count)
    for q in range(n_count): qcircuit.h(q)
    qcircuit.x(n_count)
    for q in range(n_count):
        qcircuit.append(c_amod15(a, 2 ** q), [q] + [i + n_count for i in range(4)])
    qft = QFTGate(n_count).inverse()
    qcircuit.append(qft, range(n_count))
    for qubit in range(n_count // 2):
        qcircuit.swap(qubit, n_count - qubit - 1)
    qcircuit.measure(range(n_count), range(n_count))
    return qcircuit

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_shor', methods=['POST'])
def run_shor():
    data = request.json
    N = int(data.get('N', 15))
    a = int(data.get('a', 2))
    
    start_time = time.time()
    
    if N != 15:
        return jsonify({"error": "Ten demonstrator obsługuje tylko N=15 (specyfika obwodu)."}), 400

    try:
        qc = shor_circuit(a)
        simulator = AerSimulator()
        compiled = transpile(qc, simulator)
        result = simulator.run(compiled, shots=1024).result()
        counts = result.get_counts()

        os.makedirs("static", exist_ok=True)
        unique_id = str(uuid.uuid4())
        circuit_path = f"static/circuit_{unique_id}.png"
        histo_path = f"static/histo_{unique_id}.png"

        qc.draw(output='mpl', filename=circuit_path)
        fig = plot_histogram(counts)
        fig.savefig(histo_path)

        measured = max(counts, key=counts.get)
        decimal = int(measured, 2)
        phase = decimal / (2 ** 8)
        r = Fraction(phase).limit_denominator(15).denominator
        
        factors = "Nie znaleziono"
        if r % 2 == 0:
            f1 = gcd(pow(a, r // 2) - 1, N)
            f2 = gcd(pow(a, r // 2) + 1, N)
            if f1 * f2 == N and f1 != 1:
                factors = f"{f1} x {f2}"

        return jsonify({
            "success": True,
            "r": r,
            "factors": factors,
            "circuit_url": f"/{circuit_path}",
            "histo_url": f"/{histo_path}",
            "runtime": round(time.time() - start_time, 2),
            "counts": counts
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)