/**
 * Selfie Studio i18n — tiny dictionary, no framework.
 * Locale follows the plugin bridge context unless the user toggles manually
 * (override kept in localStorage).
 */

const DICT = {
  zh: {
    'brand.sub': '自拍工坊',
    'brand.note': '穿搭与场景会在角色自拍时作为参考图使用',

    'nav.wardrobe': '衣橱',
    'nav.scenes': '场景',
    'nav.studio': '试拍',
    'nav.catalog': '目录播报',

    'wardrobe.title': '衣橱',
    'wardrobe.sub': '管理角色的穿搭单品，自拍时会自动穿上',
    'scenes.title': '场景',
    'scenes.sub': '管理自拍的环境与地点参考',

    'studio.title': '试拍',
    'studio.sub': '选择穿搭与场景，立即生成一张预览自拍',
    'studio.pickOutfit': '选择穿搭',
    'studio.pickScene': '选择场景',
    'studio.multi': '可多选',
    'studio.single': '单选',
    'studio.pose': '自拍描述',
    'studio.posePh': '例：坐在落地窗边，手捧热拿铁，侧头看向窗外的午后光',
    'studio.refOrder': '参考图顺序：人设 → 穿搭 → 场景',
    'studio.shoot': '按下快门',
    'studio.emptyTitle': '还没有作品',
    'studio.emptySub': '选好穿搭与场景，按下快门试一张',
    'studio.emptyWardrobe': '衣橱里还没有可用的穿搭，先去上传几件',
    'studio.emptyScenes': '还没有可用场景，也可以不选直接拍',
    'studio.needPrompt': '先写一句自拍描述',
    'studio.download': '下载原图',
    'studio.again': '再拍一张',
    'studio.copyTag': '复制 dressup 标签',
    'studio.loading': '取景中',
    'studio.emptyLibrary': '衣橱还空着',

    'catalog.title': '目录播报',
    'catalog.sub': '每轮对话注入角色系统提示的衣橱目录，角色据此使用 dressup 标签',
    'catalog.hint': '开关位于 WebUI 的插件设置页。停用的单品不会出现在目录中。',
    'catalog.on': '播报已开启',
    'catalog.off': '播报已关闭',

    'actions.upload': '上传',
    'actions.cancel': '取消',
    'actions.save': '保存',
    'actions.delete': '删除',
    'actions.search': '搜索名称或备注',
    'actions.edit': '编辑',
    'actions.pause': '停用',
    'actions.resume': '启用',
    'actions.off': '已停用',

    'upload.wardrobe': '上传到衣橱',
    'upload.scenes': '上传到场景',
    'upload.drop': '拖拽图片到此处，或点击选择',
    'upload.formats': '支持 PNG · JPEG · WebP，单张不超过 10 MB',
    'upload.start': '开始上传',
    'upload.working': '上传中',
    'upload.queueEmpty': '还没有选择图片',
    'upload.namePh': '名称',
    'upload.notePh': '备注（可选）',

    'edit.wardrobe': '编辑单品',
    'edit.scenes': '编辑场景',
    'edit.name': '名称',
    'edit.category': '类别',
    'edit.note': '备注',
    'edit.notePh': '给角色的提示，例如颜色、材质、氛围',
    'edit.inUse': '参与自拍',

    'confirm.deleteTitle': '删除单品',
    'confirm.deleteText': '确定要删除“{name}”吗？图片文件会一并移除，此操作不可恢复。',

    'empty.wardrobe.title': '衣橱还空着',
    'empty.wardrobe.sub': '拖入角色的第一件穿搭，或点击上传',
    'empty.wardrobe.cta': '上传穿搭',
    'empty.scenes.title': '还没有场景',
    'empty.scenes.sub': '上传一张地点或环境参考图',
    'empty.scenes.cta': '上传场景',
    'empty.filter': '没有匹配的单品',

    'cat.all': '全部',
    'cat.top': '上装',
    'cat.bottom': '下装',
    'cat.dress': '连衣裙',
    'cat.shoes': '鞋履',
    'cat.accessory': '配饰',
    'cat.other': '其他',
    'cat.indoor': '室内',
    'cat.outdoor': '户外',
    'cat.urban': '街景',
    'cat.nature': '自然',
    'cat.vehicle': '出行',

    'toast.uploaded': '已上传 {name}',
    'toast.uploadFailed': '{name} 上传失败：{reason}',
    'toast.saved': '已保存更改',
    'toast.deleted': '已删除 {name}',
    'toast.loadFailed': '数据加载失败：{reason}',
    'toast.copied': '标签已复制到剪贴板',
    'toast.copyFailed': '复制失败，请手动复制',
    'toast.someFailed': '部分图片上传失败',
  },

  en: {
    'brand.sub': 'Selfie Studio',
    'brand.note': 'Outfits and scenes are used as reference images when the character takes selfies',

    'nav.wardrobe': 'Wardrobe',
    'nav.scenes': 'Scenes',
    'nav.studio': 'Test shot',
    'nav.catalog': 'Catalog feed',

    'wardrobe.title': 'Wardrobe',
    'wardrobe.sub': 'Curate outfit pieces the character wears in selfies',
    'scenes.title': 'Scenes',
    'scenes.sub': 'Curate places and environments for selfies',

    'studio.title': 'Test shot',
    'studio.sub': 'Pick an outfit and a scene, then render a preview selfie',
    'studio.pickOutfit': 'Outfits',
    'studio.pickScene': 'Scene',
    'studio.multi': 'multi',
    'studio.single': 'single',
    'studio.pose': 'Selfie description',
    'studio.posePh': 'e.g. by the floor-to-ceiling window with a warm latte, glancing at the afternoon light',
    'studio.refOrder': 'Reference order: persona → outfits → scene',
    'studio.shoot': 'Shoot',
    'studio.emptyTitle': 'No shots yet',
    'studio.emptySub': 'Pick an outfit and a scene, then press the shutter',
    'studio.emptyWardrobe': 'The wardrobe has no enabled outfits yet — upload a few first',
    'studio.emptyScenes': 'No enabled scenes yet — you can still shoot without one',
    'studio.needPrompt': 'Write a selfie description first',
    'studio.download': 'Download',
    'studio.again': 'Shoot again',
    'studio.copyTag': 'Copy dressup tag',
    'studio.loading': 'FRAMING',
    'studio.emptyLibrary': 'The wardrobe is empty',

    'catalog.title': 'Catalog feed',
    'catalog.sub': 'The wardrobe catalog injected into the system prompt each turn — this is how the character learns the dressup tag',
    'catalog.hint': 'The toggle lives in the plugin settings page. Disabled items never appear in the catalog.',
    'catalog.on': 'Feed on',
    'catalog.off': 'Feed off',

    'actions.upload': 'Upload',
    'actions.cancel': 'Cancel',
    'actions.save': 'Save',
    'actions.delete': 'Delete',
    'actions.search': 'Name or note',
    'actions.edit': 'Edit',
    'actions.pause': 'Disable',
    'actions.resume': 'Enable',
    'actions.off': 'OFF',

    'upload.wardrobe': 'Upload to wardrobe',
    'upload.scenes': 'Upload to scenes',
    'upload.drop': 'Drag & drop images here, or click to browse',
    'upload.formats': 'PNG · JPEG · WebP, up to 10 MB each',
    'upload.start': 'Start upload',
    'upload.working': 'Uploading',
    'upload.queueEmpty': 'No images selected yet',
    'upload.namePh': 'Name',
    'upload.notePh': 'Note (optional)',

    'edit.wardrobe': 'Edit item',
    'edit.scenes': 'Edit scene',
    'edit.name': 'Name',
    'edit.category': 'Category',
    'edit.note': 'Note',
    'edit.notePh': 'A hint for the character: color, fabric, mood',
    'edit.inUse': 'Available for selfies',

    'confirm.deleteTitle': 'Delete item',
    'confirm.deleteText': 'Delete “{name}”? The image file is removed too. This cannot be undone.',

    'empty.wardrobe.title': 'An empty wardrobe',
    'empty.wardrobe.sub': 'Drop the first outfit, or click to upload',
    'empty.wardrobe.cta': 'Upload outfits',
    'empty.scenes.title': 'No scenes yet',
    'empty.scenes.sub': 'Upload a photo of a place or an environment',
    'empty.scenes.cta': 'Upload scenes',
    'empty.filter': 'Nothing matches this filter',

    'cat.all': 'All',
    'cat.top': 'Tops',
    'cat.bottom': 'Bottoms',
    'cat.dress': 'Dresses',
    'cat.shoes': 'Footwear',
    'cat.accessory': 'Accessories',
    'cat.other': 'Other',
    'cat.indoor': 'Indoor',
    'cat.outdoor': 'Outdoor',
    'cat.urban': 'Urban',
    'cat.nature': 'Nature',
    'cat.vehicle': 'On the move',

    'toast.uploaded': 'Uploaded {name}',
    'toast.uploadFailed': 'Failed to upload {name}: {reason}',
    'toast.saved': 'Changes saved',
    'toast.deleted': 'Deleted {name}',
    'toast.loadFailed': 'Failed to load data: {reason}',
    'toast.copied': 'Tag copied to clipboard',
    'toast.copyFailed': 'Copy failed — please copy manually',
    'toast.someFailed': 'Some images failed to upload',
  },
};

let locale = 'zh';
const listeners = [];

export function setLocale(next) {
  locale = DICT[next] ? next : 'zh';
  document.documentElement.setAttribute('lang', locale);
  for (const fn of listeners) fn(locale);
}

export function getLocale() {
  return locale;
}

export function onLocaleChange(fn) {
  listeners.push(fn);
}

export function t(key, vars) {
  let text = DICT[locale][key] ?? DICT.zh[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}

/** Replace text of all [data-i18n] nodes and placeholders of [data-i18n-ph]. */
export function applyStatic() {
  document.querySelectorAll('[data-i18n]').forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-ph]').forEach((node) => {
    node.setAttribute('placeholder', t(node.dataset.i18nPh));
  });
}
