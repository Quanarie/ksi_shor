import math

import matplotlib
matplotlib.use('Agg')

from flask import Flask, render_template, request, jsonify
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFTGate, UnitaryGate
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
from fractions import Fraction
from math import gcd
import numpy as np
import os
import uuid
import time

app = Flask(__name__)

def c_amodN(a, power, N, n_qubits):
    
    if gcd(a, N) != 1 or a <= 1 or a >= N:
        raise ValueError("a must be coprime with N and between 2 and N-1")

    size = 2 ** n_qubits

    U = np.zeros((size, size))

    multiplier = pow(a, power, N)

    for x in range(N):
        y = (multiplier * x) % N
        U[y][x] = 1

    # Stany powyżej N pozostają bez zmian
    for x in range(N, size):
        U[x][x] = 1

    gate = UnitaryGate(U)

    gate.name = f"{a}^{power} mod {N}"

    return gate.control()

def shor_circuit(a, N, n_count=8):
    n_target = math.ceil(math.log2(N))

    qcircuit = QuantumCircuit(n_count + n_target, n_count)

    for q in range(n_count): qcircuit.h(q)
    qcircuit.x(n_count)
    for q in range(n_count):
        qcircuit.append(c_amodN(a, 2 ** q, N, n_target), [q] + [i + n_count for i in range(n_target)])

    qft = QFTGate(n_count).inverse()
    qcircuit.append(qft, range(n_count))
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
    
    #if N not in [15, 21, 35]:
    #    return jsonify({"error": "Ten demonstrator obsługuje tylko N=15, 21, 35 (specyfika kodu)."}), 400

    try:
        n_count = math.ceil(math.log2(N)) * 2
        qc = shor_circuit(a, N, n_count)
        simulator = AerSimulator()
        compiled = transpile(qc, simulator)
        result = simulator.run(compiled, shots=1024).result()
        counts = result.get_counts()

        os.makedirs("static", exist_ok=True)
        unique_id = str(uuid.uuid4())
        circuit_path = f"static/circuit_{unique_id}.png"
        histo_path = f"static/histo_{unique_id}.png"

        qc.draw(output='mpl', filename=circuit_path, fold = -1)
        fig = plot_histogram(counts, number_to_keep=10)
        fig.savefig(histo_path)

        measured = max(counts, key=counts.get)
        decimal = int(measured, 2)
        phase = decimal / (2 ** n_count)
        fraction = Fraction(phase).limit_denominator(N)

        candidate_r = fraction.denominator
        r = candidate_r
        while pow(a, r, N) != 1:
            r += candidate_r
            if r > N:
                raise ValueError("Failed to determine correct period")
        
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
    
@app.route('/benchmark', methods=['GET'])
def run_benchmark():
    test_cases = [15, 21, 35]
    a_value = 2 
    results = []
    
    simulator = AerSimulator()
    
    for N in test_cases:
        start_time = time.time()
        
        try:
            n_count = math.ceil(math.log2(N)) * 2
            qc = shor_circuit(a_value, N, n_count)
            
            # Transpilacja, aby uzyskać dokładne statystyki dla symulatora
            compiled = transpile(qc, simulator)
            
            # Odpalamy z mniejszą liczbą strzałów (shots), aby benchmark działał trochę szybciej
            simulator.run(compiled, shots=100).result()
            
            exec_time = round(time.time() - start_time, 2)
            
            results.append({
                "N": N,
                "qubits": compiled.num_qubits,
                "depth": compiled.depth(),
                "time": exec_time
            })
        except Exception as e:
            results.append({
                "N": N,
                "error": str(e)
            })
            
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)