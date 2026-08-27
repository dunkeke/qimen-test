'use strict';

/**
 * 奇门“四害”宫位判定。
 *
 * 当前采用常见时家转盘口径：空亡、门迫、六仪击刑、奇仪入墓。
 * 规则集中在本模块中，避免界面层各自判断，后续也便于增加门派配置。
 */

const PALACES = {
    '1': { name: '坎', direction: '正北', element: '水', branches: ['子'] },
    '2': { name: '坤', direction: '西南', element: '土', branches: ['未', '申'] },
    '3': { name: '震', direction: '正东', element: '木', branches: ['卯'] },
    '4': { name: '巽', direction: '东南', element: '木', branches: ['辰', '巳'] },
    '5': { name: '中', direction: '中宫', element: '土', branches: [] },
    '6': { name: '乾', direction: '西北', element: '金', branches: ['戌', '亥'] },
    '7': { name: '兑', direction: '正西', element: '金', branches: ['酉'] },
    '8': { name: '艮', direction: '东北', element: '土', branches: ['丑', '寅'] },
    '9': { name: '离', direction: '正南', element: '火', branches: ['午'] }
};

const DOOR_ELEMENTS = {
    '休门': '水', '生门': '土', '伤门': '木', '杜门': '木',
    '景门': '火', '死门': '土', '惊门': '金', '开门': '金'
};

const OVERCOMES = { '木': '土', '土': '水', '水': '火', '火': '金', '金': '木' };

// 六仪所遁六甲落到相刑宫位。
const JI_XING = {
    '3': { stem: '戊', hiddenJia: '甲子戊', relation: '子刑卯' },
    '2': { stem: '己', hiddenJia: '甲戌己', relation: '戌刑未' },
    '8': { stem: '庚', hiddenJia: '甲申庚', relation: '申刑寅' },
    '9': { stem: '辛', hiddenJia: '甲午辛', relation: '午自刑' },
    '4': [
        { stem: '壬', hiddenJia: '甲辰壬', relation: '辰自刑' },
        { stem: '癸', hiddenJia: '甲寅癸', relation: '寅刑巳' }
    ]
};

// 奇仪入墓：同一角宫可能含两个地支；乙同时按未、戌两处标记。
const TOMB_STEMS = {
    '2': { stems: ['乙', '癸'], branch: '未' },
    '4': { stems: ['辛', '壬'], branch: '辰' },
    '6': { stems: ['乙', '丙', '戊'], branch: '戌' },
    '8': { stems: ['丁', '己', '庚'], branch: '丑' }
};

const TYPES = ['空亡', '门迫', '击刑', '入墓'];

function addHarm(items, type, code, reason, evidence) {
    items.push({ type, code, reason, evidence });
}

function calculateSiHai(pan) {
    const byGong = {};
    const counts = Object.fromEntries(TYPES.map(type => [type, 0]));
    const emptyPalaces = new Set((pan.kongWangGong || []).map(String));
    const emptyBranches = Array.from(new Set(pan.kongWangZhi || []));

    for (let number = 1; number <= 9; number++) {
        const gong = String(number);
        const palace = PALACES[gong];
        const items = [];
        const door = pan.baMen && pan.baMen[gong];
        const stem = pan.tianPan && pan.tianPan[gong];

        if (emptyPalaces.has(gong)) {
            const branches = palace.branches.filter(branch => emptyBranches.includes(branch));
            addHarm(
                items,
                '空亡',
                'kong-wang',
                `${branches.length ? branches.join('、') : emptyBranches.join('、')}空亡落${palace.name}${gong}宫`,
                { branches: branches.length ? branches : emptyBranches }
            );
        }

        const doorElement = DOOR_ELEMENTS[door];
        if (doorElement && OVERCOMES[doorElement] === palace.element) {
            addHarm(
                items,
                '门迫',
                'men-po',
                `${door}（${doorElement}）克${palace.name}宫（${palace.element}）`,
                { door, doorElement, palaceElement: palace.element }
            );
        }

        const jiXingRules = Array.isArray(JI_XING[gong]) ? JI_XING[gong] : (JI_XING[gong] ? [JI_XING[gong]] : []);
        const jiXing = jiXingRules.find(rule => rule.stem === stem);
        if (jiXing) {
            addHarm(
                items,
                '击刑',
                'ji-xing',
                `${jiXing.hiddenJia}落${palace.name}${gong}宫（${jiXing.relation}）`,
                { stem, hiddenJia: jiXing.hiddenJia, relation: jiXing.relation }
            );
        }

        const tomb = TOMB_STEMS[gong];
        if (tomb && tomb.stems.includes(stem)) {
            addHarm(
                items,
                '入墓',
                'ru-mu',
                `天盘${stem}落${palace.name}${gong}宫，入${tomb.branch}墓`,
                { stem, branch: tomb.branch }
            );
        }

        items.forEach(item => { counts[item.type] += 1; });
        byGong[gong] = items;
    }

    const affectedGongs = Object.keys(byGong).filter(gong => byGong[gong].length > 0);
    const stackedGongs = affectedGongs.filter(gong => byGong[gong].length > 1);

    return {
        ruleSet: {
            name: '常用时家转盘四害',
            version: '1.0',
            types: TYPES,
            note: '门派口径可能存在差异；本结果仅作传统文化研究与排盘辅助。'
        },
        byGong,
        summary: {
            counts,
            total: TYPES.reduce((sum, type) => sum + counts[type], 0),
            affectedGongs,
            stackedGongs
        }
    };
}

module.exports = {
    calculateSiHai,
    PALACES,
    DOOR_ELEMENTS,
    JI_XING,
    TOMB_STEMS
};
