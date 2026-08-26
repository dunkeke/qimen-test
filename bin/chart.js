#!/usr/bin/env node
'use strict';

const { calculateLifeKline } = require('../lib/lifekline');

const payload = JSON.parse(process.argv[2] || '{}');
const birthDate = new Date(payload.birthDate);
if (Number.isNaN(birthDate.getTime())) {
    process.stderr.write('birthDate must be a valid ISO date\n');
    process.exit(2);
}

try {
    const queryDate = payload.queryDate ? new Date(payload.queryDate) : birthDate;
    if (Number.isNaN(queryDate.getTime())) throw new Error('queryDate must be a valid ISO date');
    const result = calculateLifeKline(
        birthDate,
        Number(payload.startYear),
        Number(payload.endYear),
        { purpose: payload.purpose || '综合', location: payload.location || '默认位置' },
        queryDate
    );
    result.question = payload.question || '';
    process.stdout.write(JSON.stringify(result));
} catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
}
