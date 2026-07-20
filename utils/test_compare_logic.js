// 测试 JSON 对比工具的核心逻辑（差异检测）

function typeOf(v) {
    if (v === null) return 'null';
    if (Array.isArray(v)) return 'array';
    return typeof v;
}
function isLeaf(v) {
    return v === null || (typeof v !== 'object');
}
function getStatus(left, right, ignoreCase) {
    if (left === undefined) return 'missing-left';
    if (right === undefined) return 'missing-right';
    const tl = typeOf(left), tr = typeOf(right);
    if (tl !== tr) return 'typemismatch';
    if (isLeaf(left)) {
        let a = left, b = right;
        if (ignoreCase && typeof a === 'string' && typeof b === 'string') {
            a = a.toLowerCase(); b = b.toLowerCase();
        }
        return a === b ? 'same' : 'different';
    }
    return 'container';
}
function collectDiffs(left, right, path, diffs, ignoreCase) {
    const status = getStatus(left, right, ignoreCase);
    if (status === 'different' || status === 'typemismatch') {
        diffs.push({ path: path.slice(), status });
        return;
    }
    if (status === 'missing-left' || status === 'missing-right') {
        diffs.push({ path: path.slice(), status });
        return;
    }
    if (status === 'same') return;
    if (left === undefined || right === undefined) return;
    const keysL = Array.isArray(left) ? left.map((_, i) => i) : Object.keys(left);
    const keysR = Array.isArray(right) ? right.map((_, i) => i) : Object.keys(right);
    const allKeys = [...new Set([...keysL.map(String), ...keysR.map(String)])];
    for (const k of allKeys) {
        const vl = Array.isArray(left) ? left[Number(k)] : (left ? left[k] : undefined);
        const vr = Array.isArray(right) ? right[Number(k)] : (right ? right[k] : undefined);
        collectDiffs(vl, vr, [...path, k], diffs, ignoreCase);
    }
}

// ===== 测试用例 =====
let pass = 0, fail = 0;
function assert(name, cond) {
    if (cond) { pass++; console.log(`  ✅ ${name}`); }
    else { fail++; console.log(`  ❌ ${name}`); }
}

console.log("测试1: 完全相同");
let diffs = [];
collectDiffs({a:1,b:"x"}, {a:1,b:"x"}, [], diffs, true);
assert("无差异", diffs.length === 0);

console.log("测试2: 值不同");
diffs = [];
collectDiffs({temp:25}, {temp:26}, [], diffs, true);
assert("检测到1个different", diffs.length === 1 && diffs[0].status === 'different');
assert("路径正确", diffs[0].path.join('.') === 'temp');

console.log("测试3: 左缺字段");
diffs = [];
collectDiffs({a:1}, {a:1, b:2}, [], diffs, true);
assert("b 字段 missing-left", diffs.length === 1 && diffs[0].status === 'missing-left' && diffs[0].path[0]==='b');

console.log("测试4: 右缺字段");
diffs = [];
collectDiffs({a:1, b:2}, {a:1}, [], diffs, true);
assert("b 字段 missing-right", diffs.length === 1 && diffs[0].status === 'missing-right' && diffs[0].path[0]==='b');

console.log("测试5: 嵌套对象差异");
diffs = [];
collectDiffs({condition:{temp:25, humi:60}}, {condition:{temp:26, humi:60}}, [], diffs, true);
assert("检测到 condition.temp 不同", diffs.length === 1 && diffs[0].path.join('.') === 'condition.temp');

console.log("测试6: 类型不同");
diffs = [];
collectDiffs({temp:25}, {temp:"25"}, [], diffs, true);
assert("检测到 typemismatch", diffs.length === 1 && diffs[0].status === 'typemismatch');

console.log("测试7: 数组差异");
diffs = [];
collectDiffs({hourly:[1,2,3]}, {hourly:[1,9,3]}, [], diffs, true);
assert("检测到 hourly[1] 不同", diffs.length === 1 && diffs[0].path.join('.') === 'hourly.1');

console.log("测试8: 忽略大小写");
diffs = [];
collectDiffs({s:"ABC"}, {s:"abc"}, [], diffs, true);
assert("忽略大小写后相同", diffs.length === 0);
diffs = [];
collectDiffs({s:"ABC"}, {s:"abc"}, [], diffs, false);
assert("不忽略大小写检测到不同", diffs.length === 1);

console.log("测试9: null 处理");
diffs = [];
collectDiffs({a:null}, {a:null}, [], diffs, true);
assert("null 相同无差异", diffs.length === 0);
diffs = [];
collectDiffs({a:null}, {a:1}, [], diffs, true);
assert("null vs number typemismatch", diffs.length === 1 && diffs[0].status === 'typemismatch');

console.log("测试10: 模拟天气接口(温度不同, 湿度缺失)");
const leftJson = { current: { temp: 25, humidity: 60, wind: "3级" }, aqi: { value: 80 } };
const rightJson = { current: { temp: 26, wind: "3级", pressure: 1010 }, aqi: { value: 80, pm25: 35 } };
diffs = [];
collectDiffs(leftJson, rightJson, [], diffs, true);
console.log("  差异列表:");
diffs.forEach(d => console.log(`    ${d.path.join('.')} -> ${d.status}`));
assert("温度不同", diffs.some(d => d.path.join('.')==='current.temp' && d.status==='different'));
assert("湿度国际缺(missing-right)", diffs.some(d => d.path.join('.')==='current.humidity' && d.status==='missing-right'));
assert("气压国内缺(missing-left)", diffs.some(d => d.path.join('.')==='current.pressure' && d.status==='missing-left'));
assert("pm25国内缺(missing-left)", diffs.some(d => d.path.join('.')==='aqi.pm25' && d.status==='missing-left'));

console.log("\n" + "=".repeat(50));
console.log(`结果: ${pass} 通过, ${fail} 失败`);
process.exit(fail > 0 ? 1 : 0);
