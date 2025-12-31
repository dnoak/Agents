import numpy as np
import matplotlib.pyplot as plt

# ---------------- SETUP ----------------
plt.ion()
fig, ax = plt.subplots(figsize=(6, 6))

GRID_RES = 100
LIM = 1.0

ax.set_xlim(-LIM, LIM)
ax.set_ylim(-LIM, LIM)
ax.set_title("Heatmap (x1, x2) → y")

# heatmap criado UMA VEZ
heatmap = ax.imshow(
    np.zeros((GRID_RES, GRID_RES)),
    extent=(-LIM, LIM, -LIM, LIM),
    origin="lower",
    cmap="Blues",
    vmin=0.0,
    vmax=1.0,
    aspect="auto"
)

plt.colorbar(heatmap, ax=ax, label="y")

# ---------------- FUNÇÃO UPDATE ----------------
def update_heatmap(points, values, sigma=0.1):
    points = np.asarray(points)
    values = np.asarray(values)

    xi = np.linspace(-LIM, LIM, GRID_RES)
    yi = np.linspace(-LIM, LIM, GRID_RES)
    xi, yi = np.meshgrid(xi, yi)

    zi = np.zeros_like(xi)

    for (px, py), v in zip(points, values):
        zi += v * np.exp(
            -((xi - px)**2 + (yi - py)**2) / (2 * sigma**2)
        )

    # normaliza pra [0,1]
    zi -= zi.min()
    zi /= (zi.max() + 1e-8)

    heatmap.set_data(zi)



# ---------------- LOOP DE TESTE ----------------
for _ in range(100):
    n = 200
    points = np.random.uniform(-1, 1, size=(n, 2))
    values = np.random.rand(n)

    update_heatmap(points, values)

    fig.canvas.draw_idle()
    fig.canvas.flush_events()
    plt.pause(0.05)
