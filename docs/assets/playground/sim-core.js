export function seededRandom(seed) {
  if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) {
    throw new RangeError("A simulation seed must be an unsigned 32-bit integer.");
  }
  let value = seed;
  return () => {
    value = (value + 0x6d2b79f5) >>> 0;
    let mixed = Math.imul(value ^ (value >>> 15), 1 | value);
    mixed ^= mixed + Math.imul(mixed ^ (mixed >>> 7), 61 | mixed);
    return ((mixed ^ (mixed >>> 14)) >>> 0) / 4294967296;
  };
}

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

export class Terrarium {
  constructor(seed, rules = { population: 18, exploration: 35, persistence: 70 }) {
    this.seed = seed;
    this.random = seededRandom(seed);
    this.columns = 31;
    this.rows = 19;
    this.home = 9 * this.columns + 15;
    this.resources = new Uint8Array(this.columns * this.rows);
    this.obstacles = new Uint8Array(this.resources.length);
    this.trails = new Float32Array(this.resources.length);
    this.agents = [];
    this.delivered = 0;
    this.steps = 0;
    this.rules = {};
    this.setRules(rules);
    for (const [x, y] of [[5, 4], [25, 14], [25, 4]]) {
      for (const offset of [0, 1, this.columns]) this.resources[y * this.columns + x + offset] = 8;
    }
    for (let y = 6; y <= 12; y++) {
      if (y !== 8) this.obstacles[y * this.columns + 10] = 1;
      if (y !== 10) this.obstacles[y * this.columns + 20] = 1;
    }
    this.rebuildPaths();
  }

  setRules(rules) {
    for (const name of ["population", "exploration", "persistence"]) {
      const value = rules[name] ?? this.rules[name];
      const [low, high] = name === "population" ? [6, 36] : [0, 100];
      if (!Number.isInteger(value) || value < low || value > high) {
        throw new RangeError(`Invalid terrarium ${name}: ${value}`);
      }
      this.rules[name] = value;
    }
    while (this.agents.length < this.rules.population) {
      this.agents.push({ cell: this.home, previous: -1, carrying: false });
    }
    // Retiring agents drop carried food; only arrivals at home count as deliveries.
    for (const agent of this.agents.slice(this.rules.population)) {
      if (!agent.carrying) continue;
      const cell = agent.cell !== this.home && this.resources[agent.cell] < 12 ? agent.cell :
        this.resources.findIndex((food, index) => food < 12 && !this.obstacles[index] && index !== this.home);
      if (cell < 0) throw new Error("No space remains for a retiring agent's food.");
      this.resources[cell]++;
    }
    this.agents.length = this.rules.population;
  }

  neighbors(cell) {
    const x = cell % this.columns, y = Math.floor(cell / this.columns);
    return [
      x > 0 ? cell - 1 : -1, x < this.columns - 1 ? cell + 1 : -1,
      y > 0 ? cell - this.columns : -1, y < this.rows - 1 ? cell + this.columns : -1,
    ].filter(next => next >= 0 && !this.obstacles[next]);
  }

  distances(sources) {
    const distance = new Int16Array(this.resources.length).fill(-1);
    const queue = new Uint16Array(distance.length);
    let start = 0, end = 0;
    for (const cell of sources) {
      distance[cell] = 0;
      queue[end++] = cell;
    }
    while (start < end) {
      const cell = queue[start++];
      for (const next of this.neighbors(cell)) {
        if (distance[next] >= 0) continue;
        distance[next] = distance[cell] + 1;
        queue[end++] = next;
      }
    }
    return distance;
  }

  rebuildPaths() {
    this.homeDistance = this.distances([this.home]);
    this.foodDistance = this.distances(
      Array.from(this.resources.keys()).filter(cell => this.resources[cell] > 0),
    );
  }

  place(cell, tool) {
    if (!Number.isInteger(cell) || cell < 0 || cell >= this.resources.length) {
      throw new RangeError("The terrarium cursor is outside the world.");
    }
    if (!["resource", "obstacle", "erase"].includes(tool)) throw new Error("Unknown terrarium tool.");
    if (cell === this.home) return "The double ring is home; keep it open.";
    if (tool === "obstacle" && this.agents.some(agent => agent.cell === cell)) {
      return "An agent is here. Choose an empty cell for a wall.";
    }
    if (tool === "resource") {
      if (this.obstacles[cell]) return "Erase this wall before placing food.";
      if (this.resources[cell] >= 12) return "This cell already holds its limit of 12 food units.";
      const available = 192 - this.foodRemaining() - this.agents.filter(agent => agent.carrying).length;
      if (available <= 0) return "The world holds at most 192 food units. Let the agents return some.";
      this.resources[cell] += Math.min(4, 12 - this.resources[cell], available);
    } else if (tool === "obstacle") {
      if (!this.obstacles[cell] && this.obstacles.reduce((a, b) => a + b, 0) >= 128) {
        return "The world holds at most 128 walls. Erase one to place another.";
      }
      this.obstacles[cell] = 1;
      this.resources[cell] = 0;
      this.trails[cell] = 0;
    } else {
      this.obstacles[cell] = 0;
      this.resources[cell] = 0;
      this.trails[cell] = 0;
    }
    this.rebuildPaths();
    return `${tool === "resource" ? "Food added" : tool === "obstacle" ? "Wall placed" : "Cell cleared"}.`;
  }

  foodRemaining() {
    return this.resources.reduce((a, b) => a + b, 0);
  }

  step() {
    this.steps++;
    const decay = 0.72 + this.rules.persistence * 0.0027;
    for (let cell = 0; cell < this.trails.length; cell++) {
      this.trails[cell] = this.trails[cell] < 0.015 ? 0 : this.trails[cell] * decay;
    }
    let foodChanged = false;
    for (const agent of this.agents) {
      if (agent.carrying && agent.cell === this.home) {
        agent.carrying = false;
        this.delivered++;
      }
      if (!agent.carrying && this.resources[agent.cell]) {
        this.resources[agent.cell]--;
        agent.carrying = true;
        foodChanged = true;
      }
      let choices = this.neighbors(agent.cell);
      if (!choices.length) continue;
      if (agent.carrying && this.homeDistance[agent.cell] >= 0) {
        const best = Math.min(...choices.map(cell => this.homeDistance[cell]).filter(n => n >= 0));
        choices = choices.filter(cell => this.homeDistance[cell] === best);
        this.trails[agent.cell] = Math.min(8, this.trails[agent.cell] + 1.4);
      } else {
        if (choices.length > 1) choices = choices.filter(cell => cell !== agent.previous);
        if (this.random() > this.rules.exploration / 100) {
          const scent = cell => {
            const distance = this.foodDistance[cell];
            return this.trails[cell] + (distance >= 0 && distance < 7 ? (7 - distance) * 2 : 0);
          };
          const best = Math.max(...choices.map(scent));
          choices = choices.filter(cell => scent(cell) >= best - 0.1);
        }
      }
      const next = choices[Math.floor(this.random() * choices.length)];
      agent.previous = agent.cell;
      agent.cell = next;
    }
    if (foodChanged) this.rebuildPaths();
  }
}

export class SignalGame {
  constructor(seed) {
    const random = seededRandom(seed);
    this.columns = 13;
    this.rows = 9;
    this.player = { x: 6, y: 4 };
    this.fragments = [[1, 1], [11, 7], [1, 7], [11, 1], [6, 0], [12, 4], [6, 8], [0, 4]]
      .map(([x, y]) => ({ x, y }));
    for (let i = this.fragments.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [this.fragments[i], this.fragments[j]] = [this.fragments[j], this.fragments[i]];
    }
    this.noise = [[2, 4], [4, 6], [6, 2], [8, 4], [10, 2], [6, 6]].map(([x, y], index) => ({
      x, y, baseX: x, baseY: y, phase: random() * Math.PI * 2, vertical: index % 2 === 0,
    }));
    this.elapsed = 0;
    this.physicsTime = 0;
    this.cooldown = 0;
    this.collected = 0;
    this.hits = 0;
    this.state = "ready";
  }

  get target() { return this.fragments[this.collected]; }
  get remaining() { return Math.max(0, 60 - this.elapsed); }

  start() {
    if (this.state === "ready") this.state = "playing";
  }

  update(dt, direction, manual = false) {
    if (!Number.isFinite(dt) || dt <= 0 || dt > (manual ? 0.5 : 0.1)) {
      throw new RangeError("Signal/noise requires a bounded positive timestep.");
    }
    if (!Number.isFinite(direction.x) || !Number.isFinite(direction.y)) {
      throw new RangeError("Signal direction must be finite.");
    }
    if (this.state !== "playing") return;
    this.elapsed = Math.min(60, this.elapsed + dt);
    this.physicsTime += dt;
    this.cooldown = Math.max(0, this.cooldown - dt);
    const magnitude = Math.hypot(direction.x, direction.y);
    if (magnitude > 0) {
      const distance = manual ? 1 : 5 * dt;
      this.player.x = clamp(this.player.x + direction.x / magnitude * distance, 0, 12);
      this.player.y = clamp(this.player.y + direction.y / magnitude * distance, 0, 8);
    }
    for (const noise of this.noise) {
      const drift = manual ? 0 : Math.sin(this.physicsTime * 0.9 + noise.phase) * 0.7;
      noise.x = noise.baseX + (noise.vertical ? 0 : drift);
      noise.y = noise.baseY + (noise.vertical ? drift : 0);
    }
    if (this.cooldown === 0 && this.noise.some(noise =>
      Math.hypot(noise.x - this.player.x, noise.y - this.player.y) < 0.56)) {
      this.hits++;
      this.elapsed = Math.min(60, this.elapsed + 3);
      this.cooldown = 1;
      this.player.x = 6;
      this.player.y = 4;
    }
    if (this.remaining === 0) {
      this.state = "lost";
      return;
    }
    if (Math.hypot(this.target.x - this.player.x, this.target.y - this.player.y) < 0.62) {
      this.collected++;
      if (this.collected === this.fragments.length) this.state = "won";
    }
  }
}
