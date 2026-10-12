# 🟡 Pac-Man

A desktop recreation of the classic arcade maze chase game. Navigate the maze, consume all pellets, evade enemy ghosts, and turn the tables with Power Pellets!

---

## 🎮 Features

- **Grid & Maze Navigation**: Tile-based movement with intersection turn-buffering to prevent getting stuck on wall corners.
- **Side Wrap Tunnels**: Horizontal border tunnels that seamlessly teleport Pac-Man and ghosts across the screen.
- **Ghost AI State Machine**:
  - **Scatter**: Ghosts retreat to their designated corners of the maze.
  - **Chase**: Ghosts pursue Pac-Man based on target-tile tracking.
  - **Frightened**: Ghosts turn blue, slow down, and become edible after Pac-Man eats a Power Pellet.
- **Scoring & Combo Multiplier**:
  - Regular Pellets: +10 pts
  - Power Pellets: +50 pts
  - Edible Ghosts: 200 → 400 → 800 → 1600 pts chain multiplier
- **Lives & Game Loop**: Real-time HUD displaying score, remaining lives, and game over / restart states.

---

## 🛠️ Built With

- **Language**: Python 3 *(or update if using JavaScript / C)*
- **Framework / Library**: Pygame *(or HTML5 Canvas / Raylib / ncurses)*

---

## 🚀 Getting Started

### Prerequisites

Make sure you have Python 3 installed on your machine.
- Python 3.8+
- Pygame (`pip install pygame`)

### Installation & Running

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/pacman.git](https://github.com/YOUR_USERNAME/pacman.git)
   cd pacman 
