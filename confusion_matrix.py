import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import confusion_matrix

# Your confusion matrix data
cm = np.array([[4632, 115],
               [131, 6452]])

# Create the plot
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
ax.figure.colorbar(im, ax=ax)

# Add labels
ax.set(xticks=np.arange(cm.shape[1]),
       yticks=np.arange(cm.shape[0]),
       xticklabels=['Legitimate', 'Phishing'],
       yticklabels=['Legitimate', 'Phishing'],
       title='Confusion Matrix - Logistic Regression Model',
       ylabel='Actual Label',
       xlabel='Predicted Label')

# Add text annotations
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        ax.text(j, i, format(cm[i, j], ',d'),
                ha="center", va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "black")

plt.tight_layout()
plt.savefig('confusion_matrix.png', dpi=150)
plt.show()
