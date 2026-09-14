// Scratch is a finite drawing language, not JavaScript. All positions use a 400 x 400 sheet.
export const LIMITS = Object.freeze({
  source: 16000, tokens: 12000, nodes: 4096, depth: 32, nesting: 8,
  repeat: 512, operations: 6000, steps: 12000, logs: 40, value: 1000000, milliseconds: 120,
});

const COLORS = new Set(["forest", "green", "stone", "paper", "white", "ink"]);
const FUNCTIONS = Object.freeze({
  sin: (degrees) => Math.sin(degrees * Math.PI / 180),
  cos: (degrees) => Math.cos(degrees * Math.PI / 180),
  abs: Math.abs,
  sqrt: Math.sqrt,
});
const ARITY = Object.freeze({ line: 4, circle: 3, rect: 4, width: 1, print: 1 });
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

export class DrawingError extends Error {
  constructor(message, token = { line: 1, column: 1 }) {
    super(`Line ${token.line}, column ${token.column}: ${message}`);
    this.name = "DrawingError";
    this.line = token.line;
    this.column = token.column;
  }
}

export function executeDrawing(source, { now = () => performance.now() } = {}) {
  const start = now();
  const checkTime = (token) => {
    if (now() - start > LIMITS.milliseconds) throw new DrawingError("Time budget reached. Use fewer repeats.", token);
  };
  if (typeof source !== "string") throw new DrawingError("Code must be text.");
  if (source.length > LIMITS.source) throw new DrawingError(`Code is limited to ${LIMITS.source.toLocaleString("en-US")} characters.`);
  const tokens = [];
  let offset = 0, line = 1, column = 1;
  while (offset < source.length) {
    const character = source[offset];
    if (character === " " || character === "\t" || character === "\r") { offset++; column++; continue; }
    if (character === "#") {
      while (offset < source.length && source[offset] !== "\n") { offset++; column++; }
      continue;
    }
    const position = { line, column };
    let value, type;
    if (character === "\n") {
      value = "\n"; type = "separator"; offset++; line++; column = 1;
    } else if (character === ";") {
      value = ";"; type = "separator"; offset++; column++;
    } else if (/[0-9.]/.test(character)) {
      const match = /^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/.exec(source.slice(offset));
      if (!match) throw new DrawingError("Expected a number after the decimal point.", position);
      value = match[0]; type = "number"; offset += value.length; column += value.length;
    } else if (/[a-zA-Z_]/.test(character)) {
      value = /^[a-zA-Z_][a-zA-Z_0-9]*/.exec(source.slice(offset))[0];
      type = "name"; offset += value.length; column += value.length;
    } else if ("+-*/(),{}=".includes(character)) {
      value = character; type = "symbol"; offset++; column++;
    } else {
      throw new DrawingError(`Unexpected ${JSON.stringify(character)}. This is drawing code, not JavaScript or a shell.`, position);
    }
    tokens.push({ type, value, ...position });
    if (tokens.length > LIMITS.tokens) throw new DrawingError("Too many tokens. Shorten the drawing.", position);
    checkTime(position);
  }
  tokens.push({ type: "end", value: "", line, column });
  let cursor = 0, nodes = 0;
  const peek = () => tokens[cursor];
  const take = () => tokens[cursor++];
  const expect = (value) => {
    const token = take();
    if (token.value !== value) throw new DrawingError(`Expected "${value}", found ${token.value ? JSON.stringify(token.value) : "end of code"}.`, token);
    return token;
  };
  const name = () => {
    const token = take();
    if (token.type !== "name") throw new DrawingError("Expected a variable name.", token);
    return token;
  };
  const node = (value) => {
    if (++nodes > LIMITS.nodes) throw new DrawingError("Drawing is too complex. Use fewer expressions.", value.token);
    return value;
  };
  const separators = () => { while (peek().type === "separator") take(); };

  function expression(minimum = 0, depth = 0) {
    if (depth > LIMITS.depth) throw new DrawingError("Expression nesting is too deep.", peek());
    const token = take();
    let result;
    if (token.type === "number") {
      result = node({ kind: "number", value: Number(token.value), token });
    } else if (token.value === "-" || token.value === "+") {
      result = node({ kind: "unary", sign: token.value, argument: expression(3, depth + 1), token });
    } else if (token.value === "(") {
      result = expression(0, depth + 1);
      expect(")");
    } else if (token.type === "name") {
      if (peek().value === "(") {
        if (!own(FUNCTIONS, token.value)) throw new DrawingError(`Unknown function "${token.value}". Try sin, cos, abs or sqrt.`, token);
        take();
        const argument = expression(0, depth + 1);
        expect(")");
        result = node({ kind: "call", name: token.value, argument, token });
      } else result = node({ kind: "variable", name: token.value, token });
    } else throw new DrawingError("Expected a number, variable or parenthesized expression.", token);
    while (true) {
      const operator = peek();
      const precedence = operator.value === "+" || operator.value === "-" ? 1
        : operator.value === "*" || operator.value === "/" ? 2 : 0;
      if (!precedence || precedence <= minimum) break;
      take();
      result = node({ kind: "binary", operator: operator.value, left: result,
        right: expression(precedence, depth + 1), token: operator });
    }
    return result;
  }

  function block(nesting = 0) {
    if (nesting > LIMITS.nesting) throw new DrawingError("Repeat nesting is limited to eight levels.", peek());
    const statements = [];
    separators();
    while (peek().type !== "end" && peek().value !== "}") {
      checkTime(peek());
      const token = name();
      const statement = { kind: token.value, token };
      if (token.value === "let") {
        statement.name = name().value;
        expect("=");
        statement.value = expression();
      } else if (token.value === "repeat") {
        statement.count = expression();
        expect("as");
        statement.name = name().value;
        expect("{");
        statement.body = block(nesting + 1);
        expect("}");
      } else if (token.value === "clear" || token.value === "color") {
        const color = name();
        if (!COLORS.has(color.value)) throw new DrawingError("Choose forest, green, stone, paper, white or ink.", color);
        statement.color = color.value;
      } else if (own(ARITY, token.value)) {
        statement.arguments = [];
        for (let index = 0; index < ARITY[token.value]; index++) {
          if (index) expect(",");
          statement.arguments.push(expression());
        }
      } else throw new DrawingError(`Unknown command "${token.value}". Open Language guide for the command list.`, token);
      statements.push(node(statement));
      if (!["separator", "end"].includes(peek().type) && peek().value !== "}") {
        throw new DrawingError("Put each command on a new line or separate commands with a semicolon.", peek());
      }
      separators();
    }
    return statements;
  }
  const ast = block();
  if (peek().type !== "end") throw new DrawingError('Unexpected "}". No repeat is open here.', peek());
  if (!ast.length) throw new DrawingError("Write a drawing command or choose an example first.");
  const operations = [], logs = [];
  let steps = 0, evaluations = 0;
  const finite = (value, token) => {
    if (!Number.isFinite(value) || Math.abs(value) > LIMITS.value) {
      throw new DrawingError("Numbers must be finite and between -1,000,000 and 1,000,000. Check division and square roots.", token);
    }
    return value;
  };
  function evaluate(value, scope, depth = 0) {
    if (depth > LIMITS.depth) throw new DrawingError("Expression is too long or deeply nested.", value.token);
    if (++evaluations % 64 === 0) checkTime(value.token);
    let result;
    switch (value.kind) {
      case "number": result = value.value; break;
      case "variable":
        if (!scope.has(value.name)) throw new DrawingError(`Unknown variable "${value.name}". Define it with let first.`, value.token);
        result = scope.get(value.name); break;
      case "call": result = FUNCTIONS[value.name](evaluate(value.argument, scope, depth + 1)); break;
      case "unary": result = (value.sign === "-" ? -1 : 1) * evaluate(value.argument, scope, depth + 1); break;
      case "binary": {
        const left = evaluate(value.left, scope, depth + 1), right = evaluate(value.right, scope, depth + 1);
        switch (value.operator) {
          case "+": result = left + right; break;
          case "-": result = left - right; break;
          case "*": result = left * right; break;
          case "/": result = left / right; break;
        }
        break;
      }
    }
    return finite(result, value.token);
  }
  function run(statements, scope) {
    for (const statement of statements) {
      if (++steps > LIMITS.steps) throw new DrawingError("Execution budget reached. Reduce repeats.", statement.token);
      checkTime(statement.token);
      if (statement.kind === "let") {
        if (scope.size >= 256 && !scope.has(statement.name)) throw new DrawingError("At most 256 variables are allowed.", statement.token);
        scope.set(statement.name, evaluate(statement.value, scope));
      } else if (statement.kind === "repeat") {
        const count = evaluate(statement.count, scope);
        if (!Number.isInteger(count) || count < 0 || count > LIMITS.repeat) {
          throw new DrawingError("Repeat needs a whole number from 0 to 512.", statement.token);
        }
        for (let index = 0; index < count; index++) {
          if (++steps > LIMITS.steps) throw new DrawingError("Execution budget reached. Reduce repeats.", statement.token);
          checkTime(statement.token);
          const local = new Map(scope);
          local.set(statement.name, index);
          run(statement.body, local);
        }
      } else if (statement.kind === "print") {
        if (logs.length >= LIMITS.logs) throw new DrawingError("Log budget reached (40 lines). Print less often.", statement.token);
        logs.push(String(evaluate(statement.arguments[0], scope)));
      } else {
        const args = statement.arguments?.map((argument) => evaluate(argument, scope));
        if (statement.kind === "width" && (args[0] < 0.2 || args[0] > 20)) {
          throw new DrawingError("Line width must be from 0.2 to 20.", statement.token);
        }
        if (statement.kind === "circle" && (args[2] < 0 || args[2] > 2000)) {
          throw new DrawingError("Circle radius must be from 0 to 2,000.", statement.token);
        }
        if (operations.length >= LIMITS.operations) throw new DrawingError("Drawing budget reached (6,000 operations). Reduce repeats.", statement.token);
        operations.push({ command: statement.kind, ...(args ? { args } : { color: statement.color }) });
      }
    }
  }
  run(ast, new Map());
  checkTime(peek());
  return { operations, logs, steps };
}
