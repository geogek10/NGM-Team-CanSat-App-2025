#include "include/TurboCodec.hpp"

#include <iostream>
#include <fstream>
#include <string>
#include <sstream>

void trimNewline(std::string &str) {
    while (!str.empty() && (str.back() == '\\')) {
        str.pop_back();
    }
}

int main() {
    TurboCodec codec; // Instantiate the TurboCodec class for encoding/decoding operations.
    std::string input, encodedOutput, decodedOutput; // Strings to hold the input, encoded, and decoded messages.
    char option; // Variable to store user menu option.
    double noiseVariance = 0.5; // Initial noise variance value, representing the noise level in the channel.
    int maxIterations = 20; // Default maximum number of decoding iterations.
    double convergenceThreshold = 0.001; // Default threshold for detecting convergence in decoding.

    // Όνομα αρχείου εισόδου και εξόδου
    const std::string inputFileName = "Turbo_Codes_Data.csv";
    const std::string outputBCJRFileName = "BCJR_Output.csv";
    const std::string outputMAPFileName = "MAP_Output.csv";
    const std::string outputSOVAFileName = "SOVA_Output.csv";
    const std::string outputHYBRIDFileName = "HYBRID_Output.csv";

    // Άνοιγμα του αρχείου εισόδου για ανάγνωση
    std::ifstream inputFile(inputFileName);
    if (!inputFile.is_open()) {
        std::cerr << "Failed to open input file: " << inputFileName << std::endl;
        return 1;
    }

    // Άνοιγμα του αρχείου εξόδου για εγγραφή
    std::ofstream outputFileBCJR(outputBCJRFileName);
    if (!outputFileBCJR.is_open()) {
        std::cerr << "Failed to open output file: " << outputBCJRFileName << std::endl;
        return 1;
    }

    // Άνοιγμα του αρχείου εξόδου για εγγραφή
    std::ofstream outputFileMAP(outputMAPFileName);
    if (!outputFileMAP.is_open()) {
        std::cerr << "Failed to open output file: " << outputMAPFileName << std::endl;
        return 1;
    }

    // Άνοιγμα του αρχείου εξόδου για εγγραφή
    std::ofstream outputFileSOVA(outputSOVAFileName);
    if (!outputFileSOVA.is_open()) {
        std::cerr << "Failed to open output file: " << outputSOVAFileName << std::endl;
        return 1;
    }

    std::ofstream outputFileHYBRID(outputHYBRIDFileName);
    if (!outputFileHYBRID.is_open()) {
        std::cerr << "Failed to open output file: " << outputHYBRIDFileName << std::endl;
        return 1;
    }

    // Διαβάζουμε γραμμή-γραμμή από το αρχείο εισόδου
    std::string line;
    std::string dexodedBCJRline;
    std::string dexodedMAPline;
    std::string dexodedSOVAline;
    std::string dexodedHYBRIDline;

    while (std::getline(inputFile, line)) {
        size_t commaPos = line.find(',');
        if (commaPos != std::string::npos) {
            std::string firstColumn = line.substr(0, commaPos);
            std::string secondColumn = line.substr(commaPos + 1);
            for (size_t i = 0; i < 5; i++)
            {
                secondColumn.pop_back();
            }
            trimNewline(secondColumn);

            codec.decode(secondColumn, dexodedBCJRline, noiseVariance, "BCJR");
            codec.decode(secondColumn, dexodedMAPline, noiseVariance, "MAP");
            codec.decode(secondColumn, dexodedSOVAline, noiseVariance, "SOVA");
            codec.decode(secondColumn, dexodedHYBRIDline, noiseVariance, "HYBRID");

            // Γράφουμε τη γραμμή στο αρχείο εξόδου
            outputFileBCJR << firstColumn << "," << dexodedBCJRline << '\n';
            outputFileMAP << firstColumn << "," << dexodedMAPline << '\n';
            outputFileSOVA << firstColumn << "," << dexodedSOVAline << '\n';
            outputFileHYBRID << firstColumn << "," << dexodedHYBRIDline << '\n';
            std::cout << firstColumn << " | " << secondColumn << std::endl;
        }
    }

    // Κλείνουμε τα αρχεία
    inputFile.close();
    outputFileBCJR.close();
    outputFileMAP.close();
    outputFileSOVA.close();
    outputFileHYBRID.close();

    std::cout << "Data Decoded successfully !!! " << std::endl;

    return 0;
}
