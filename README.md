# AAE5303 Environment Check

This repository is a **smoke test** for your AAE5303 / robotics environment.

If you can:

1. Run the Python checks without errors; and  
2. Build and run the ROS 2 talker/listener example;

then your **Ubuntu + ROS 2 + Python** setup is good enough for this subject.

---

## 1. Target environment

This repo assumes you are using:

- **Ubuntu 22.04 LTS**
- **ROS 2 Humble** (installed from the official instructions)
- **Python 3.10+**

You can be on:

- Native Ubuntu (dual‑boot or bare metal), or  
- Ubuntu in WSL2 / VM / Docker – as long as ROS 2 and Python work.

> ⚠️ This repo does **not** install ROS 2 for you.  
> Follow the official ROS 2 Humble installation guide first, then come back here.

---

## 2. Clone the repository

From your Ubuntu shell:

```bash
cd ~
git clone https://github.com/<your-org>/aae5303-env-check.git
cd aae5303-env-check
