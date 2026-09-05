import { Router } from './ui/router';
import { renderMenu } from './ui/menu';

const root = document.getElementById('app');
if (!root) throw new Error('#app root element missing');

const router = new Router(root);
router.navigate(renderMenu);
