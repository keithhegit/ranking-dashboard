export const PRODUCTS = ['ugphone', 'ldcloud', 'redfinger', 'vsphone'];

export const APP_IDS = {
  ugphone: 'com.tykeji.ugphone',
  ldcloud: 'com.ld.cph.gl',
  redfinger: 'com.redfinger.global',
  vsphone: 'com.vsphone.overseas',
};

export const COUNTRIES = [
  'TH',
  'BR',
  'PH',
  'US',
  'VN',
  'TR',
  'MX',
  'HK',
  'TW',
  'ID',
  'KR',
  'JP',
  'DE',
  'GB',
  'PL',
  'FR',
  'MY',
  'IT',
  'SG',
  'IN',
];

export const COUNTRY_NAMES = {
  TH: '泰国',
  BR: '巴西',
  PH: '菲律宾',
  US: '美国',
  VN: '越南',
  TR: '土耳其',
  MX: '墨西哥',
  HK: '香港',
  TW: '台湾',
  ID: '印度尼西亚',
  KR: '韩国',
  JP: '日本',
  DE: '德国',
  GB: '英国',
  PL: '波兰',
  FR: '法国',
  MY: '马来西亚',
  IT: '意大利',
  SG: '新加坡',
  IN: '印度',
};

export const MARKET_TIERS = {
  focus: {
    label: '重点市场',
    countries: ['TH', 'VN', 'PH', 'BR', 'TR', 'MY', 'ID', 'HK'],
  },
  potential: {
    label: '潜力国家',
    countries: ['TW', 'KR', 'US', 'MX', 'SG', 'JP', 'PL', 'DE', 'GB', 'IN', 'IT', 'FR'],
  },
  all: {
    label: '全部国家',
    countries: COUNTRIES,
  },
};

export const BRAND_LABELS = {
  ugphone: 'UGPhone',
  ldcloud: 'LDCloud',
  redfinger: 'Redfinger',
  vsphone: 'VSPhone',
};

export const CRON_TIMEZONE_NOTE =
  'Cloudflare cron triggers use UTC; Asia/Shanghai midnight is 16:00 UTC on the previous calendar day.';
