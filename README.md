# Settlers of Catan Placement Algorithm

An algorithm designed to determine optimal settlement placements in *Settlers of Catan* against random-placing bots. Includes backtesting and hyperparameter tuning to maximize win rate.

---

## Overview

This project simulates *Settlers of Catan* games to find the most effective starting settlement placements. It contains:
1. A full game engine
2. A scoring-based settlement placement algorithm
3. Bot gameplay logic

The primary tool is `src/main.py`, where you can run simulations by setting the `TRIALS` parameter. This runs a “smart” placement bot against three random-placement opponents, tracking win rate, average points, and game length.

You can experiment with the placement algorithm’s parameters (found at the top of `src/bot.py`) to attempt to improve win rate. Additionally, optional **Optuna**-based hyperparameter tuning code is included for automated optimization.

---

## Features

- **Full Catan Game Engine:** Includes longest road/largest army logic, random board/development card generation, ports, and more.
- **Advanced Placement Algorithm:** Uses a multi-factor scoring system with 30+ levers—taking into account pip count, resource synergy, port value, and node synergies based on common strategies (e.g., Ore-Wheat-Sheep, Road, Balanced, Cities & Roads, Port-focused).
- **Bot Gameplay Logic:** Supports building priorities, development card use, port & bank trading, and robbing the leader. (Bot-to-bot trade is a planned feature.)
- **Hyperparameter Tuning:** Integrates **Optuna** for advanced tuning of the placement strategy parameters.
- **Backtesting Framework:** Run simulations with adjustable trial count and randomized turn orders to robustly measure performance.

---

## Installation

Clone the repository and install dependencies:
```bash
git clone <repo-url>
cd <project-folder>
pip install -r requirements.txt
