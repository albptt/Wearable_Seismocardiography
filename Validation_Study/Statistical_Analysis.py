'''
To verify the applicability of a measuring instrument in a clinical context, it is necessary to evaluate its validity and reliability (intra and inter-operator). 
In the case where the instrument operates without the intervention of an operator, the validity of its measurements remains the only determining parameter. 
It is necessary to compare the new measuring instrument under analysis with an already certified and validated one, which is considered the gold standard. 
If it is demonstrated that the distributions of the measurements of the two devices are strongly correlated, and this statement has statistical significance, 
then the validity of the measurements of the new measuring instrument has been proven.
To verify the correlation between the two data distributions, it is first necessary to determine whether these distributions are normal or not. 
If both distributions are normal, then the Pearson coefficient is used; otherwise, the Spearman rank correlation coefficient is used. 
The normality of the data in the case of small sample sizes is assessed using the Shapiro-Wilk test.
Both of the quantitative analyses described above have a qualitative counterpart consisting of interpretable graphs: 
QQ-plot for checking normality and Bland-Altman plot for checking correlation. 
If the calculated validity coefficient exceeds the threshold of 0.7, then the new measuring instrument is considered valid. 
An interpretation commonly used for the correlation coefficient is: 0.90 to 1.00 = excellent, 0.70 to 0.89 = good, 0.50 to 0.69 = moderate, 0.30 to 0.49 = low, <0.30 negligible. 
The minimum number of data for distribution must be 20 (significance 0.05 (alpha), power 0.20 (beta), assuming a moderate correlation between measurements).

Per verificare l'applicabilità di uno strumento di misura in ambito clinico è necessario valutarne validità ed affidabilità (intra e inter operatore).
Nel caso in cui tale strumento operi senza l'intervento di un operatore, la validità delle sue misure rimane l'unico parametro determinante.
Si deve quindi confrontare il nuovo strumento di misura sotto analisi con uno già certificato e validato, il quale viene considerato gold standard.
Se si dimostra che le distribuzioni delle misure dei due dispositivi sono fortemente correlate e questa affermazione ha significatività statistica
allora si ha dimostrato la validità delle misure del nuovo strumento di misura.
Per verificare la correlazione fra le due distribuzioni di dati bisogna innanzitutto determinare la normalità o meno di tali distribuzioni.
Se entrambe le distribuzioni risultano normali, allora si utilizza il coefficiente di Pearson, altrimenti il coefficiente di correlazione per ranghi di Spearman.
La normalità dei dati in caso di campioni di piccole dimensioni è valutata tramite il test di Shapiro-Wilk.
Entrambe le analisi quantitative appena descritte hanno una controparte qualitativa che consiste in grafici interpretabili:
QQ-plot per la verifica di normalità e Bland-Altman plot per la verifica di correlazione.
Se il coefficiente di validità calcolato supera la soglia di 0.7 allora il nuovo strumento di misura è considerabile valido.
Un'interpretazione comunemente utilizzata per il coefficiente di correlazione è: 0.90 to 1.00 = eccellente, 0.70 to 0.89 = buona, 0.50 to 0.69 = moderata, 0.30 to 0.49 = bassa, <0.30 trascurabile.
Il numero minimo di dati per distribuzione deve essere di 20 (significatività 0.05 (alpha), power 0.20 (beta), assumendo una correlazione moderata fra misure)

Pozzolo P. Coefficiente di correlazione lineare r di Pearson. Published 2020. Accessed June 28, 2022. https://paolapozzolo.it/coefficiente-correlazione-statistica-pearson/
Pozzolo P. La distribuzione normale spiegata semplice. Published 2020. Accessed June 28, 2022. https://paolapozzolo.it/distribuzione-normale/
F. Jacobs, J. Scheerhoorn, E. Mestrom, J. van der Stam, R. Arthur Bouwman, and S. Nienhuijs, “Reliability of heart rate and respiration rate measurements with a wireless accelerometer in postbariatric recovery,” PLoS One, vol. 16, no. 4 April 2021, 2021, doi: 10.1371/journal.pone.0247903.
M. M. Mukaka, “Correlation coefficient and its use,” Malawi Med. J., vol. 24, no. September, pp. 69-71, 2012.
M. Parati et al., “Video-based Goniometer Applications for Measuring Knee Joint Angles during Walking in Neurological Patients: A Validity, Reliability and Usability Study,” Sensors, vol. 23, no. 4, 2023, doi: 10.3390/s23042232.

'''

import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy import stats
from scipy.stats import shapiro
from scipy.stats import pearsonr
from scipy.stats import spearmanr

################################################################################################################################

# Si verifica quantitativamente e qualitativamente la normalità di entrambe le distribuzioni

################################################################################################################################

# Verifica quantitativa della normalità

# Vettore di dati HEA
vettore_HEA = []

# Test di Shapiro-Wilk per normalità
statistica_test, p_value = shapiro(vettore_HEA)

# Stampa i risultati
print(f"Statistica del test: {statistica_test}")
print(f"P-value: {p_value}")

# Confronta il p-value con un livello di significatività (solitamente 0.05)
livello_significatività = 0.05
if p_value > livello_significatività:
    print("Non possiamo rifiutare l'ipotesi nulla (i dati seguono una distribuzione normale)")
else:
    print("Rifiutiamo l'ipotesi nulla (i dati non seguono una distribuzione normale)")

################################################################################################################################

# Verifica qualitativa della normalità

# Calcola i quantili teorici della distribuzione normale
quantili_teorici = np.percentile(vettore_HEA, np.linspace(0, 100, len(vettore_HEA)))

# Calcola i quantili empirici del tuo vettore di dati
quantili_empirici = np.percentile(np.random.normal(size=len(vettore_HEA)), np.linspace(0, 100, len(vettore_HEA)))

# Crea il QQ plot
plt.scatter(quantili_teorici, quantili_empirici)
plt.plot([min(quantili_teorici), max(quantili_teorici)], [min(quantili_teorici), max(quantili_teorici)], linestyle='--', color='red', label='y=x')
plt.title("Quantile-Quantile (QQ) Plot")
plt.xlabel("Quantili teorici")
plt.ylabel("Quantili empirici")
plt.show()

################################################################################################################################

# Verifica quantitativa della normalità

# Vettore di dati PS
vettore_PS = []

# Test di Shapiro-Wilk per normalità
statistica_test, p_value = shapiro(vettore_PS)

# Stampa i risultati
print(f"Statistica del test: {statistica_test}")
print(f"P-value: {p_value}")

# Confronta il p-value con un livello di significatività (solitamente 0.05)
livello_significatività = 0.05
if p_value > livello_significatività:
    print("Non possiamo rifiutare l'ipotesi nulla (i dati seguono una distribuzione normale)")
else:
    print("Rifiutiamo l'ipotesi nulla (i dati non seguono una distribuzione normale)")

################################################################################################################################

# Verifica qualitativa della normalità

# Calcola i quantili teorici della distribuzione normale
quantili_teorici = np.percentile(vettore_PS, np.linspace(0, 100, len(vettore_PS)))

# Calcola i quantili empirici del tuo vettore di dati
quantili_empirici = np.percentile(np.random.normal(size=len(vettore_PS)), np.linspace(0, 100, len(vettore_PS)))

# Crea il QQ plot
plt.scatter(quantili_teorici, quantili_empirici)
plt.title("Quantile-Quantile (QQ) Plot")
plt.xlabel("Quantili teorici")
plt.ylabel("Quantili empirici")
plt.show()

################################################################################################################################

# Se entrambe le distribuzioni risultano normali si procede col coefficiente di Pearson

# Calcola il coefficiente di Pearson e il p-value
coeff_pearson, p_value = pearsonr(vettore_HEA, vettore_PS)

# Stampa i risultati
print(f"Coefficiente di Pearson: {coeff_pearson}")
print(f"P-value: {p_value}")

# Confronta il p-value con un livello di significatività (solitamente 0.05)
livello_significatività = 0.05
if p_value > livello_significatività:
    print("La correlazione non è statisticamente significativa")
else:
    print("La correlazione è statisticamente significativa")

################################################################################################################################

# Se almeno una delle due distribuzioni risulta non normale si procede col coefficiente di correlazione per ranghi di Spearman 

# Calcola il coefficiente di correlazione di Spearman e il p-value
coeff_spearman, p_value = spearmanr(vettore_HEA, vettore_PS)

# Stampa i risultati
print(f"Coefficiente di correlazione di Spearman: {coeff_spearman}")
print(f"P-value: {p_value}")

# Confronta il p-value con un livello di significatività (solitamente 0.05)
livello_significatività = 0.05
if p_value > livello_significatività:
    print("La correlazione non è statisticamente significativa")
else:
    print("La correlazione è statisticamente significativa")

################################################################################################################################

# Si correla il precendente risultato con un Bland-Altman plot sul quale vengono tracciati gli intervalli di confidenza 

# Calcola le differenze tra i due vettori
differenze = np.array(vettore_HEA) - np.array(vettore_PS)

# Calcola la media delle differenze
media_differenze = np.mean(differenze)

# Calcola la deviazione standard delle differenze
deviazione_standard_differenze = np.std(differenze, ddof=1)

# Crea il Bland-Altman plot
plt.scatter(np.mean([vettore_HEA, vettore_PS], axis=0), differenze)
plt.axhline(y=media_differenze, color='r', linestyle='--', label=f'Media differenze: {media_differenze:.2f}')
plt.axhline(y=media_differenze + 1.96 * deviazione_standard_differenze, color='g', linestyle='--', label='Limite superiore')
plt.axhline(y=media_differenze - 1.96 * deviazione_standard_differenze, color='g', linestyle='--', label='Limite inferiore')
plt.xlabel('Media dei due metodi')
plt.ylabel('Differenze tra i metodi')
plt.title('Bland-Altman Plot')
plt.legend()
plt.show()

################################################################################################################################