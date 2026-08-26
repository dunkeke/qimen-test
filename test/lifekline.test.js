'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { calculateLifeKline, elementRelation } = require('../lib/lifekline');

test('五行关系按生克循环计算', () => {
    assert.deepEqual(elementRelation('木', '水'), { name: '生我', score: 8 });
    assert.deepEqual(elementRelation('木', '金'), { name: '克我', score: -7 });
});

test('人生 K 线返回逐年、可解释且有界的融合结果', () => {
    const result = calculateLifeKline(new Date('1990-01-01T12:00:00'), 2025, 2027);
    assert.equal(result.points.length, 3);
    assert.deepEqual(result.points.map((point) => point.year), [2025, 2026, 2027]);
    for (const point of result.points) {
        assert.ok(point.score >= 0 && point.score <= 100);
        assert.ok(point.juShu && point.door && point.star && point.god);
    }
    assert.match(result.bazi.pillars.day, /^[甲乙丙丁戊己庚辛壬癸]/);
    assert.equal(result.queryPan.basicInfo.method, '时家');
});
