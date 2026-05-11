from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import QFTGate
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
from fractions import Fraction
from math import gcd
import os
import uuid

def c_amod15(a, power):

    if a not in [2, 4, 7, 8, 11, 13]:
        raise ValueError("a must be one of: 2,4,7,8,11,13")

    U = QuantumCircuit(4)

    for _ in range(power):

        if a in [2, 13]:
            U.swap(0, 1)
            U.swap(1, 2)
            U.swap(2, 3)

        if a in [7, 8]:
            U.swap(2, 3)
            U.swap(1, 2)
            U.swap(0, 1)

        if a in [4, 11]:
            U.swap(0, 2)
            U.swap(1, 3)

        if a in [7, 11, 13]:
            for q in range(4):
                U.x(q)

    U = U.to_gate()
    U.name = f"{a}^{power} mod 15"

    return U.control()


def shor_circuit(a, n_count=8):

    qcircuit = QuantumCircuit(n_count + 4, n_count)

    for q in range(n_count):
        qcircuit.h(q)

    qcircuit.x(n_count)

    for q in range(n_count):
        qcircuit.append(
            c_amod15(a, 2 ** q),
            [q] + [i + n_count for i in range(4)]
        )

    qft = QFTGate(n_count).inverse()

    qcircuit.append(qft, range(n_count))

    for qubit in range(n_count // 2):
        qcircuit.swap(qubit, n_count - qubit - 1)

    qcircuit.measure(range(n_count), range(n_count))

    return qcircuit

def run_circuit(qcircuit, shots=1024):

    simulator = AerSimulator()

    compiled = transpile(qcircuit, simulator)

    result = simulator.run(compiled, shots=shots).result()

    counts = result.get_counts()

    return counts


def find_period(measured_value, n_count):

    decimal = int(measured_value, 2)

    phase = decimal / (2 ** n_count)

    frac = Fraction(phase).limit_denominator(15)

    r = frac.denominator

    return r, frac


def get_factors(a, r, N):

    if r % 2 != 0:
        return None

    if pow(a, r // 2, N) == N - 1:
        return None

    factor1 = gcd(pow(a, r // 2) - 1, N)
    factor2 = gcd(pow(a, r // 2) + 1, N)

    if factor1 in [1, N] or factor2 in [1, N]:
        return None

    return factor1, factor2

def shor_algorithm(N=15, a=2, shots=1024) -> tuple[bool, int, tuple[int, int] | None, str, str]:

    factor = gcd(a, N)

    if factor != 1:
        return False, 0, None, "", ""

    qc = shor_circuit(a)

    counts = run_circuit(qc, shots=shots)

    fig = plot_histogram(counts)

    os.makedirs("static", exist_ok=True)

    circuit_filename = f"static/{uuid.uuid4()}_circuit.png"
    histogram_filename = f"static/{uuid.uuid4()}_histogram.png"

    qc.draw(output='mpl', filename=circuit_filename, fold=120)
    fig.savefig(histogram_filename)

    measured = max(counts, key=counts.get)

    r, frac = find_period(measured, 8)

    factors = get_factors(a, r, N)

    if factors:
        return True, r, factors, histogram_filename, circuit_filename
    else:
        return False, r, None, histogram_filename, circuit_filename
    
shor_algorithm()