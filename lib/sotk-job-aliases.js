/*
 * Explicit current-role aliases that map operational employee nomenclature
 * to the canonical SOTK job family. Source employee fields are never mutated.
 * Add future approved aliases here rather than broad fuzzy matching by name.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.SOTKJobAliases = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';
  const text = value => value == null ? '' : String(value).trim();
  const norm = value => text(value).toLowerCase()
    .replace(/&/g, ' dan ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');

  /**
   * PPC / Penaksir UPC on an UPC/UPS outlet is the same SOTK family as
   * PSR / Penaksir. This mapping applies to CURRENT job fields only.
   */
  function normalizeCurrentJob(input = {}) {
    const level = text(input.level).toUpperCase();
    const unitType = text(input.unitType).toUpperCase();
    const jobCode = text(input.jobCode).toUpperCase();
    const jobName = norm(input.jobName);
    const positionName = norm(input.positionName);
    const isPenaksirUpc = level === 'C'
      && unitType === 'UPC/UPS'
      && jobCode === 'PPC'
      && jobName === 'penaksir upc'
      && /^penaksir (?:upc|ups)(?: |$)/.test(positionName);

    if (isPenaksirUpc) {
      return {
        jobCode: 'PSR',
        jobName: 'Penaksir',
        alias: 'PPC_TO_PSR',
        aliasLabel: 'PPC / Penaksir UPC → PSR / Penaksir'
      };
    }

    return {
      jobCode: text(input.jobCode),
      jobName: text(input.jobName),
      alias: '',
      aliasLabel: ''
    };
  }

  /** Match the master legacy prefix "Penaksir UPC/S" to both UPC and UPS. */
  function matchesLegacyPositionPrefix(family, rulePrefix, positionName) {
    return text(family).toUpperCase() === 'PSR'
      && norm(rulePrefix) === 'penaksir upc s'
      && /^penaksir (?:upc|ups)(?: |$)/.test(norm(positionName));
  }

  return { normalizeCurrentJob, matchesLegacyPositionPrefix };
});
