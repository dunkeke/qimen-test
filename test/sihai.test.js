'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');

const { calculateSiHai } = require('../lib/sihai');

function basePan(overrides = {}) {
    return {
        tianPan: { '1': '甲', '2': '乙', '3': '丙', '4': '丁', '5': '戊', '6': '己', '7': '庚', '8': '辛', '9': '壬' },
        baMen: { '1': '休门', '2': '死门', '3': '伤门', '4': '杜门', '5': '', '6': '开门', '7': '惊门', '8': '生门', '9': '景门' },
        kongWangZhi: [],
        kongWangGong: [],
        ...overrides
    };
}

test('空亡宫去重并保留对应地支依据', () => {
    const result = calculateSiHai(basePan({ kongWangZhi: ['戌', '亥'], kongWangGong: ['6', '6'] }));
    assert.equal(result.summary.counts['空亡'], 1);
    assert.equal(result.byGong['6'][0].type, '空亡');
    assert.deepEqual(result.byGong['6'][0].evidence.branches, ['戌', '亥']);
});

test('门克宫判为门迫，宫克门不误判', () => {
    const result = calculateSiHai(basePan({
        baMen: { '1': '生门', '2': '休门', '3': '开门', '4': '惊门', '5': '', '6': '景门', '7': '死门', '8': '伤门', '9': '休门' }
    }));
    assert.ok(result.byGong['1'].some(item => item.type === '门迫'), '土门克坎水应为门迫');
    assert.ok(result.byGong['3'].some(item => item.type === '门迫'), '金门克震木应为门迫');
    assert.ok(result.byGong['6'].some(item => item.type === '门迫'), '火门克乾金应为门迫');
    assert.ok(result.byGong['9'].some(item => item.type === '门迫'), '水门克离火应为门迫');
    assert.ok(!result.byGong['2'].some(item => item.type === '门迫'), '坤土克休门水属于门受制，不是门迫');
});

test('六仪击刑按天盘干与落宫共同判断', () => {
    const result = calculateSiHai(basePan({
        tianPan: { '1': '乙', '2': '己', '3': '戊', '4': '壬', '5': '丙', '6': '丁', '7': '辛', '8': '庚', '9': '辛' }
    }));
    for (const gong of ['2', '3', '4', '8', '9']) {
        assert.ok(result.byGong[gong].some(item => item.type === '击刑'), `${gong}宫应标注击刑`);
    }
});

test('奇仪入墓覆盖坤、巽、乾、艮四个角宫', () => {
    const result = calculateSiHai(basePan({
        tianPan: { '1': '甲', '2': '癸', '3': '甲', '4': '辛', '5': '甲', '6': '丙', '7': '甲', '8': '丁', '9': '甲' }
    }));
    for (const gong of ['2', '4', '6', '8']) {
        assert.ok(result.byGong[gong].some(item => item.type === '入墓'), `${gong}宫应标注入墓`);
    }
    assert.equal(result.summary.counts['入墓'], 4);
});

test('叠加四害会进入重害宫摘要', () => {
    const result = calculateSiHai(basePan({
        tianPan: { '1': '甲', '2': '甲', '3': '甲', '4': '甲', '5': '甲', '6': '甲', '7': '甲', '8': '庚', '9': '甲' },
        baMen: { '1': '休门', '2': '死门', '3': '伤门', '4': '杜门', '5': '', '6': '开门', '7': '惊门', '8': '伤门', '9': '景门' },
        kongWangZhi: ['丑'],
        kongWangGong: ['8']
    }));
    assert.deepEqual(result.byGong['8'].map(item => item.type), ['空亡', '门迫', '击刑', '入墓']);
    assert.ok(result.summary.stackedGongs.includes('8'));
    assert.equal(result.summary.total, 4);
});
