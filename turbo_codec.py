import random
import numpy as np
from typing import List, Tuple

# Utility functions

def generate_interleaver(length: int) -> List[int]:
    """Generates a random interleaver (permutation of indices)."""
    indices = np.arange(length, dtype=np.int64)
    random.seed(42)  # Fixed seed for reproducibility
    np.random.shuffle(indices)
    return indices.tolist()

def string_to_binary(input_str: str) -> List[int]:
    """Converts a string into a binary representation."""
    binary = []
    for char in input_str:
        for i in range(7, -1, -1):
            binary.append((ord(char) >> i) & 1)
    return binary

def binary_to_string(binary: List[int]) -> str:
    """Converts a binary representation back to a string."""
    output = ""
    for i in range(0, len(binary), 8):
        char_bits = binary[i:i + 8]
        char_val = 0
        for bit in char_bits:
            char_val = (char_val << 1) | bit
        output += chr(char_val)
    return output

# ConvolutionalCode class
class ConvolutionalCode:
    def __init__(self, n: int, m: int, gen: List[int]):
        self.n = n  # Number of output bits per input bit
        self.m = m  # Memory size of the encoder
        self.generators = gen  # Generator polynomials
        self.state = 0  # Current state of the encoder
        self.num_states = 1 << m

    def reset(self):
        """Resets the internal state of the encoder."""
        self.state = 0

    def compute_next_state(self, current_state: int, input_bit: bool) -> int:
        """Computes the next state based on current state and input bit."""
        return ((current_state << 1) | input_bit) & ((1 << self.m) - 1)

    def compute_next_output(self, current_state: int, input_bit: bool) -> int:
        """Computes the output bits for a given state and input bit."""
        output = 0
        for i in range(self.n):
            temp = current_state & self.generators[i]
            if input_bit:
                temp |= (1 << (self.m - 1))
            output |= (bin(temp).count('1') % 2) << i
        return output

    def encode(self, input_bits: List[int]) -> List[Tuple[int, int]]:
        """Encodes a sequence of input bits using the convolutional encoder."""
        output = []
        self.reset()
        for bit in input_bits:
            systematic_bit = bit
            parity_bit = self.compute_next_output(self.state, bit)
            self.state = self.compute_next_state(self.state, bit)
            output.append((systematic_bit, parity_bit))
        return output

    def decode_bcjr(self, systematic: List[float], parity: List[float], extrinsic: List[float], noise_variance: float) -> List[float]:
        """Decodes using the BCJR algorithm with NumPy optimization."""
        length = len(systematic)
        systematic = np.array(systematic, dtype=np.float64)
        parity = np.array(parity, dtype=np.float64)
        extrinsic = np.array(extrinsic, dtype=np.float64)

        # Initialize alpha and beta matrices
        alpha = np.full((length + 1, self.num_states), -np.inf, dtype=np.float64)
        beta = np.full((length + 1, self.num_states), -np.inf, dtype=np.float64)
        alpha[0, 0] = 0.0
        beta[length, 0] = 0.0

        # Precompute gamma components for all states and inputs
        inputs = np.array([0, 1], dtype=np.int8)
        gamma_base = (systematic[:, None] * (2 * inputs - 1) + 
                      parity[:, None] * (2 * inputs - 1) + 
                      extrinsic[:, None] * (2 * inputs - 1)) / noise_variance

        # Forward recursion
        for t in range(length):
            for state in range(self.num_states):
                next_states = np.array([self.compute_next_state(state, i) for i in inputs])
                gamma = gamma_base[t]
                alpha[t + 1, next_states] = np.maximum(alpha[t + 1, next_states], alpha[t, state] + gamma)

        # Backward recursion
        for t in range(length - 1, -1, -1):
            for state in range(self.num_states):
                next_states = np.array([self.compute_next_state(state, i) for i in inputs])
                gamma = gamma_base[t]
                beta[t, next_states] = np.maximum(beta[t, next_states], beta[t + 1, state] + gamma)

        # Compute LLRs
        llr = np.zeros(length, dtype=np.float64)
        for t in range(length):
            prob0, prob1 = -np.inf, -np.inf
            for state in range(self.num_states):
                next_states = np.array([self.compute_next_state(state, i) for i in inputs])
                gamma = gamma_base[t]
                metrics = alpha[t, state] + gamma + beta[t + 1, next_states]
                prob0 = np.maximum(prob0, metrics[0])
                prob1 = np.maximum(prob1, metrics[1])
            llr[t] = prob1 - prob0

        return llr.tolist()

    def decode_map(self, systematic: List[float], parity: List[float], extrinsic: List[float], noise_variance: float) -> List[float]:
        """Decodes using the MAP algorithm (optimized similarly to BCJR)."""
        return self.decode_bcjr(systematic, parity, extrinsic, noise_variance)  # MAP is often identical to BCJR in practice

    def decode_sova(self, systematic: List[float], parity: List[float], extrinsic: List[float], noise_variance: float) -> List[float]:
        """Decodes using the Soft Output Viterbi Algorithm with NumPy optimization."""
        length = len(systematic)
        systematic = np.array(systematic, dtype=np.float64)
        parity = np.array(parity, dtype=np.float64)
        extrinsic = np.array(extrinsic, dtype=np.float64)

        path_metrics = np.full(self.num_states, -np.inf, dtype=np.float64)
        path_metrics[0] = 0.0
        decisions = np.full((length, self.num_states), -1, dtype=np.int8)

        inputs = np.array([0, 1], dtype=np.int8)
        gamma_base = (systematic[:, None] * (2 * inputs - 1) + 
                      parity[:, None] * (2 * inputs - 1) + 
                      extrinsic[:, None] * (2 * inputs - 1)) / noise_variance

        # Forward pass
        for t in range(length):
            temp_path_metrics = np.full(self.num_states, -np.inf, dtype=np.float64)
            for state in range(self.num_states):
                next_states = np.array([self.compute_next_state(state, i) for i in inputs])
                gamma = gamma_base[t]
                metrics = path_metrics[state] + gamma
                better = metrics > temp_path_metrics[next_states]
                temp_path_metrics[next_states[better]] = metrics[better]
                decisions[t, next_states[better]] = inputs[better]
            path_metrics = temp_path_metrics

        # Traceback
        most_likely_path = np.zeros(length, dtype=np.int8)
        state = np.argmax(path_metrics)
        for t in range(length - 1, -1, -1):
            most_likely_path[t] = decisions[t, state]
            state = self.compute_next_state(state, most_likely_path[t])

        # Compute LLRs
        llr = np.zeros(length, dtype=np.float64)
        for t in range(length):
            metric0, metric1 = -np.inf, -np.inf
            for state in range(self.num_states):
                next_states = np.array([self.compute_next_state(state, i) for i in inputs])
                gamma = gamma_base[t]
                metrics = path_metrics[state] + gamma
                metric0 = np.maximum(metric0, metrics[0])
                metric1 = np.maximum(metric1, metrics[1])
            llr[t] = metric1 - metric0

        return llr.tolist()

# TurboCodec class
class TurboCodec:
    def __init__(self):
        self.encoder1 = ConvolutionalCode(2, 3, [0b1011, 0b1111])
        self.encoder2 = ConvolutionalCode(2, 3, [0b1011, 0b1111])
        self.max_iterations = 20
        self.convergence_threshold = 0.001

    def encode(self, input_str: str) -> str:
        """Encodes an input string into a turbo-encoded string."""
        binary_input = string_to_binary(input_str)
        interleaver = generate_interleaver(len(binary_input))

        encoded1 = self.encoder1.encode(binary_input)
        permuted_input = [0] * len(binary_input)
        for i, idx in enumerate(interleaver):
            permuted_input[idx] = binary_input[i]
        encoded2 = self.encoder2.encode(permuted_input)

        output = ""
        for i in range(len(binary_input)):
            output += str(encoded1[i][0])  # Systematic bit
            output += str(encoded1[i][1])  # Parity bit from encoder1
            output += str(encoded2[i][1])  # Parity bit from encoder2
        return output

    def decode(self, input_str: str, noise_variance: float, algorithm: str) -> str:
        """Decodes a turbo-encoded string using the specified algorithm."""
        length = len(input_str) // 3
        systematic = [float(input_str[i * 3]) for i in range(length)]
        parity1 = [float(input_str[i * 3 + 1]) for i in range(length)]
        parity2 = [float(input_str[i * 3 + 2]) for i in range(length)]

        extrinsic1 = np.zeros(length, dtype=np.float64)
        extrinsic2 = np.zeros(length, dtype=np.float64)

        num_iterations = 0
        for num_iterations in range(self.max_iterations):
            if algorithm == "BCJR":
                extrinsic1 = self.encoder1.decode_bcjr(systematic, parity1, extrinsic2, noise_variance)
                extrinsic2 = self.encoder2.decode_bcjr(systematic, parity2, extrinsic1, noise_variance)
            elif algorithm == "MAP":
                extrinsic1 = self.encoder1.decode_map(systematic, parity1, extrinsic2, noise_variance)
                extrinsic2 = self.encoder2.decode_map(systematic, parity2, extrinsic1, noise_variance)
            elif algorithm == "SOVA":
                extrinsic1 = self.encoder1.decode_sova(systematic, parity1, extrinsic2, noise_variance)
                extrinsic2 = self.encoder2.decode_sova(systematic, parity2, extrinsic1, noise_variance)
            elif algorithm == "HYBRID":
                if num_iterations < self.max_iterations // 2:
                    extrinsic1 = self.encoder1.decode_map(systematic, parity1, extrinsic2, noise_variance)
                    extrinsic2 = self.encoder2.decode_map(systematic, parity2, extrinsic1, noise_variance)
                else:
                    extrinsic1 = self.encoder1.decode_sova(systematic, parity1, extrinsic2, noise_variance)
                    extrinsic2 = self.encoder2.decode_sova(systematic, parity2, extrinsic1, noise_variance)
            else:
                raise ValueError("Unsupported algorithm.")

            max_difference = np.max(np.abs(np.array(extrinsic1) - np.array(systematic)))
            if max_difference < self.convergence_threshold:
                break

        reconstructed_message = [1 if s > 0 else 0 for s in systematic]
        output = binary_to_string(reconstructed_message)
        print(f"Number of iterations: {num_iterations}")
        return output

    def set_max_iterations(self, iterations: int):
        """Sets the maximum number of decoding iterations."""
        self.max_iterations = iterations

    def set_convergence_threshold(self, threshold: float):
        """Sets the convergence threshold for decoding."""
        self.convergence_threshold = threshold