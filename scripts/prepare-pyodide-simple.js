import { copyFile, readdir, mkdir } from 'fs/promises';
import { existsSync } from 'fs';

console.log('简化版Pyodide设置 - 跳过网络下载');

async function copyPyodide() {
	console.log('复制Pyodide文件到static目录');

	// 确保目录存在
	if (!existsSync('static/pyodide')) {
		await mkdir('static/pyodide', { recursive: true });
	}

	// 复制node_modules/pyodide中的所有文件到static/pyodide
	try {
		const entries = await readdir('node_modules/pyodide');
		for (const entry of entries) {
			await copyFile(`node_modules/pyodide/${entry}`, `static/pyodide/${entry}`);
			console.log(`已复制: ${entry}`);
		}
		console.log('Pyodide文件复制完成');
	} catch (error) {
		console.error('复制Pyodide文件时出错:', error);
	}
}

await copyPyodide();
console.log('简化版Pyodide设置完成');