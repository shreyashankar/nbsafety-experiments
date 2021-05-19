import { CellSlice, LocationSet, SlicedExecution, parse, slice } from "@andrewhead/python-program-analysis";
import sqlite3 from 'sqlite3';
import fs from "file-system";

function loc(line0, col0, line1 = line0 + 1, col1 = 0) {
    return { first_line: line0, first_column: col0, last_line: line1, last_column: col1 };
}

let traceID = process.argv[process.argv.length - 3];
let sessionID = process.argv[process.argv.length - 2];
let validCounters = process.argv[process.argv.length - 1];

const db = new sqlite3.Database('./data/traces.sqlite');
let sql = "select source from cell_execs where trace=" + traceID + " and session=" + sessionID + " and counter in (" + validCounters + ") order by counter";

db.all(sql, [], (err, rows) => {
    let source = rows.map(elem => elem.source);

    let ast = parse(source.join('\n'));
    let locations = slice(ast, new LocationSet(loc(ast.location.last_line - 1, 0)))
    let numLinesNeeded = Object.keys(locations._items).length;

    fs.appendFileSync('nbgather_stats.txt', "(" + traceID + ", " + sessionID + ", " + numLinesNeeded + ")\n");
})

// let source_code = process.argv[process.argv.length - 1];
// console.log(process.argv);
// let ast = parse(['a = 1', 'b = a', 'c = 3'].join('\n'));
// console.log(ast);
// let locations = slice(ast, new LocationSet(loc(3, 0)));
// console.log(locations);
// let numLinesNeeded = Object.keys(locations._items).length;