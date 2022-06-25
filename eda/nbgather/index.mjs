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

function compareLocations(a, b) {
    if (a[0] < b[0]) return -1;
    if (a[0] > b[0]) return 1;
    return 0;
}

db.all(sql, [], (err, rows) => {
    let source = rows.map(elem => elem.source.trim());

    let ast = parse(source.join('\n').trim());
    let locations = slice(ast, new LocationSet(loc(ast.location.last_line - 1, 0)))
    let splitSource = source.join('\n').trim().split('\n');
    splitSource.forEach((elem, index) => {
        console.log(index + 1, elem);
    });

    let splitSourceMap = new Map();
    for (let idx = 0; idx < splitSource.length; idx++) {
        splitSourceMap.set(idx, false);
    }

    // Create array to sort
    var locationArr = [];
    for (var item in locations._items) {
        locationArr.push(item.split(",").map(x => parseInt(x)));
    }

    locationArr.sort(compareLocations);
    // console.log(locationArr);

    // For each element in the location array, index into the line list
    // note that we are ignoring elem[1] and elem[3] here because we 
    // are not calling .slice(elem[1], elem[3])
    let nbgatherSlice = locationArr.flatMap((elem) => {
        var currSlice = [];

        // var splitSourceCopy = [...splitSource];
        // splitSourceCopy[elem[0] - 1] = splitSourceCopy[elem[0] - 1].slice(elem[1]);
        // splitSourceCopy[elem[2] - 1] = splitSourceCopy[elem[2] - 1].slice(0, elem[3]);

        // Check to see if slice is already included
        let beginIndex = elem[0] - 1;
        let endIndex = elem[3] === 0 ? elem[2] - 1 : elem[2];

        for (var i = beginIndex; i < endIndex; i++) {
            if (splitSourceMap[i] === true) {
                continue;
            }

            splitSourceMap[i] = true;
            currSlice.push(splitSource[i]);
        }

        // return splitSourceCopy.slice(elem[0] - 1, elem[2]).join('\n').trim().split('\n');
        // console.log(elem);
        // console.log(currSlice);
        // console.log(currSlice.join('\n').trim().split('\n'));
        return currSlice;
    });

    // Filters out any empty lines
    nbgatherSlice = nbgatherSlice.join("\n").split(/\n/).filter(x => x.trim().length > 0);
    console.log(locationArr);
    console.log(nbgatherSlice.join("\n"));

    let numLinesNeeded = nbgatherSlice.length;
    // fs.appendFileSync('nbgather_stats.txt', "(" + traceID + ", " + sessionID + ", " + numLinesNeeded + ")\n");

    // Write out slice
    let sliceFilename = 'results/nbgather/' + traceID + '_' + sessionID + '.txt';
    // fs.writeFileSync(sliceFilename, nbgatherSlice.join("\n"));
})