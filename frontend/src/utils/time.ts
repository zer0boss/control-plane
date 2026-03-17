/**
 * 时间格式化工具
 * 后端返回的时间已经是北京时间，需要正确显示
 */

/**
 * 格式化时间为北京时间字符串
 * @param dateString ISO 时间字符串
 * @returns 格式化后的时间字符串
 */
export function formatBeijingTime(dateString: string): string {
  if (!dateString) return '-';

  // 后端返回的时间已经是北京时间，直接解析
  const date = new Date(dateString);

  // 如果解析失败，返回原始字符串
  if (isNaN(date.getTime())) return dateString;

  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * 格式化时间为简短的时间字符串（只显示时分秒）
 * @param dateString ISO 时间字符串
 * @returns 格式化后的时间字符串
 */
export function formatBeijingTimeShort(dateString: string): string {
  if (!dateString) return '-';

  const date = new Date(dateString);

  if (isNaN(date.getTime())) return dateString;

  return date.toLocaleTimeString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

/**
 * 格式化时间为日期字符串
 * @param dateString ISO 时间字符串
 * @returns 格式化后的日期字符串
 */
export function formatBeijingDate(dateString: string): string {
  if (!dateString) return '-';

  const date = new Date(dateString);

  if (isNaN(date.getTime())) return dateString;

  return date.toLocaleDateString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/**
 * 格式化相对时间（如"刚刚"、"5分钟前"等）
 * @param dateString ISO 时间字符串
 * @returns 相对时间字符串
 */
export function formatRelativeTime(dateString: string): string {
  if (!dateString) return '-';

  const date = new Date(dateString);

  if (isNaN(date.getTime())) return dateString;

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return '刚刚';
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分钟前`;
  } else if (diffHours < 24) {
    return `${diffHours}小时前`;
  } else if (diffDays < 7) {
    return `${diffDays}天前`;
  } else {
    return formatBeijingDate(dateString);
  }
}