'use strict';

const qimen = require('./qimen');

const GAN_ELEMENT = { 甲: '木', 乙: '木', 丙: '火', 丁: '火', 戊: '土', 己: '土', 庚: '金', 辛: '金', 壬: '水', 癸: '水' };
const ELEMENT_INDEX = { 木: 0, 火: 1, 土: 2, 金: 3, 水: 4 };
const DOOR_SCORE = { 休门: 8, 生门: 14, 景门: 8, 开门: 12, 伤门: -8, 杜门: -6, 死门: -14, 惊门: -8 };
const STAR_SCORE = { 天蓬: 1, 天芮: -7, 天冲: 4, 天辅: 8, 天禽: 2, 天心: 8, 天柱: -3, 天任: 6, 天英: 5 };
const GOD_SCORE = { 值符: 10, 腾蛇: -5, 太阴: 6, 六合: 8, 白虎: -8, 玄武: -6, 九地: 5, 九天: 7 };

function elementRelation(dayElement, yearElement) {
    const delta = (ELEMENT_INDEX[yearElement] - ELEMENT_INDEX[dayElement] + 5) % 5;
    if (delta === 0) return { name: '同气', score: 5 };
    if (delta === 1) return { name: '我生', score: 2 };
    if (delta === 2) return { name: '我克', score: 4 };
    if (delta === 3) return { name: '克我', score: -7 };
    return { name: '生我', score: 8 };
}

function palaceScore(pan, gong) {
    return (DOOR_SCORE[pan.baMen[gong]] || 0) +
        (STAR_SCORE[pan.jiuXing[gong]] || 0) +
        (GOD_SCORE[pan.baShen[gong]] || 0);
}

/**
 * Build an annual “life K-line” by combining the natal day master with one
 * Qi Men chart at local noon on the birthday in every requested year.
 * Scores are an explainable visualization index, not a factual prediction.
 */
function calculateLifeKline(birthDate, startYear, endYear, options = {}) {
    const natal = qimen.calculate(birthDate, { method: '时家', ...options });
    if (natal.error) throw new Error(natal.message);
    const dayGan = natal.siZhu.day.charAt(0);
    const dayElement = GAN_ELEMENT[dayGan];
    const month = birthDate.getMonth();
    const day = birthDate.getDate();
    const points = [];

    for (let year = startYear; year <= endYear; year++) {
        // Noon avoids DST/non-existent local-hour surprises while retaining the birthday.
        const sampleDate = new Date(year, month, day, 12, 0, 0);
        const pan = qimen.calculate(sampleDate, { method: '时家', ...options });
        if (pan.error) throw new Error(pan.message);
        const yearElement = GAN_ELEMENT[pan.siZhu.year.charAt(0)];
        const relation = elementRelation(dayElement, yearElement);
        const focusGong = pan.zhiFuGong;
        const raw = 50 + relation.score + palaceScore(pan, focusGong);
        const score = Math.max(0, Math.min(100, raw));
        points.push({
            year,
            age: year - birthDate.getFullYear(),
            score,
            relation: relation.name,
            yearPillar: pan.siZhu.year,
            juShu: pan.juShu.fullName,
            focusGong,
            door: pan.baMen[focusGong],
            star: pan.jiuXing[focusGong],
            god: pan.baShen[focusGong]
        });
    }

    return {
        natal,
        bazi: { pillars: natal.siZhu, dayMaster: dayGan, dayElement },
        points,
        disclaimer: '人生 K 线为传统文化模型的可视化指数，仅供学习与娱乐，不构成决策建议。'
    };
}

module.exports = { calculateLifeKline, elementRelation, palaceScore };
