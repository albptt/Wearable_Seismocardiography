import matplotlib.pyplot as plt

def plot_vectors(vector1, vector2):
    # Crea gli array di indici per i vettori
    indices = range(1, len(vector1) + 1)

    # Primo grafico
    plt.plot(indices, vector1, marker='o', linestyle='-', color='blue', label='HEA')

    # Crea il secondo grafico con linee rosse
    plt.plot(indices, vector2, marker='o', linestyle='-', color='red', label='Pulse Oximeter')

    # Aggiungi etichette agli assi
    plt.xlabel('Measurement')
    plt.ylabel('Value')

    plt.title("Seated 1")

    # Aggiungi una legenda
    plt.legend()

    # Mostra il grafico
    plt.show()


valoriHEA = []

valoriS =  []

plot_vectors(valoriHEA, valoriS)

