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


    // console.log(source);

    // Create array to sort
    var locationArr = [];
    for (var item in locations._items) {
        locationArr.push(item.split(",").map(x => parseInt(x)));
    }

    function compareLocations(a, b) {
        if (a[0] < b[0]) return -1;
        if (a[0] > b[0]) return 1;
        return 0;
    }

    locationArr.sort(compareLocations);

    // For each element in the location array, index into the line list
    let nbgatherSlice = locationArr.map((elem) => (
        source.slice(elem[0] - 1, elem[2]).join("").slice(elem[1], elem[3])
    ));

    let numLinesNeeded = locationArr.length;
    fs.appendFileSync('nbgather_stats.txt', "(" + traceID + ", " + sessionID + ", " + numLinesNeeded + ")\n");

    // Write out slice
    let sliceFilename = 'results/nbgather/' + traceID + '_' + sessionID + '.txt';
    fs.writeFileSync(sliceFilename, nbgatherSlice.join("\n"));
})