#!/usr/bin/env node
/**
 * AI科技日报自动更新脚本
 * 定时执行搜索并更新 data.json，然后推送到 GitHub
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PROXY_PORT = process.env.AUTH_GATEWAY_PORT || '19000';
const PROXY_HOST = '127.0.0.1';
const API_PATH = '/proxy/prosearch/search';

const DATA_FILE = path.join(__dirname, 'data.json');
const DEPLOY_SCRIPT = path.join(__dirname, 'deploy.ps1');

// GitHub 配置 - 从环境变量读取
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_OWNER = process.env.GITHUB_OWNER || 'slimnexk';
const GITHUB_REPO = process.env.GITHUB_REPO || 'ai-daily';

if (!GITHUB_TOKEN) {
    console.log('⚠️ GITHUB_TOKEN 环境变量未设置，跳过部署');
}

// 搜索函数
function search(keyword) {
    return new Promise((resolve, reject) => {
        const params = { keyword };
        const requestBody = JSON.stringify(params);
        
        const req = http.request(
            {
                host: PROXY_HOST,
                port: Number(PROXY_PORT),
                path: API_PATH,
                method: 'POST',
                timeout: 15000,
                headers: {
                    'Content-Type': 'application/json',
                    'Content-Length': Buffer.byteLength(requestBody),
                },
            },
            (res) => {
                let data = '';
                res.setEncoding('utf8');
                res.on('data', (chunk) => { data += chunk; });
                res.on('end', () => {
                    try {
                        const result = JSON.parse(data);
                        resolve(result);
                    } catch (e) {
                        reject(e);
                    }
                });
            }
        );
        
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('超时'));
        });
        
        req.on('error', reject);
        req.write(requestBody);
        req.end();
    });
}

// 解析搜索结果，提取关键资讯
function parseResults(searchResult, category) {
    if (!searchResult.success || !searchResult.data) return [];
    
    const docs = searchResult.data.docs || [];
    return docs.slice(0, 3).map(doc => ({
        title: doc.title || '',
        desc: (doc.passage || '').replace(/<[^>]+>/g, '').substring(0, 100),
        solve: ''
    }));
}

// 上传到 GitHub
function deployToGitHub() {
    console.log('📤 开始部署到 GitHub...');
    
    const files = ['index.html', 'data.json'];
    
    for (const file of files) {
        const filePath = path.join(__dirname, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const base64 = Buffer.from(content).toString('base64');
        
        const body = JSON.stringify({
            message: `Update ${file}`,
            content: base64,
            branch: 'main'
        });
        
        const options = {
            hostname: 'api.github.com',
            path: `/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${file}`,
            method: 'PUT',
            headers: {
                'Authorization': `token ${GITHUB_TOKEN}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(body)
            }
        };
        
        return new Promise((resolve, reject) => {
            const req = http.request(options, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    if (res.statusCode >= 200 && res.statusCode < 300) {
                        console.log(`✓ Deployed: ${file}`);
                        resolve();
                    } else {
                        console.log(`✗ Failed: ${file} - ${res.statusCode}`);
                        resolve(); // Continue even if failed
                    }
                });
            });
            req.on('error', e => {
                console.log(`✗ Deploy error: ${e.message}`);
                resolve(); // Continue
            });
            req.write(body);
            req.end();
        });
    }
}

// 主更新流程
async function update() {
    console.log('🔍 开始搜索AI资讯...');
    
    const keywords = {
        llm: '大模型最新进展 2026',
        github: 'GitHub AI热门项目 2026',
        video: 'Sora Pika Runway 视频生成模型 2026',
        devtools: 'AI开发工具 AI编程 2026最新',
        rag: 'RAG 知识库 上下文窗口突破 2026',
        other: 'AI技术突破 2026'
    };
    
    const data = {
        date: new Date().toISOString().split('T')[0],
        llm: [],
        github: [],
        video: [],
        devtools: [],
        rag: [],
        other: []
    };
    
    // 执行搜索
    for (const [key, keyword] of Object.entries(keywords)) {
        try {
            console.log(`搜索: ${keyword}`);
            const result = await search(keyword);
            data[key] = parseResults(result, key);
            console.log(`✓ ${key}: 获取到 ${data[key].length} 条结果`);
        } catch (e) {
            console.error(`✗ ${key}: 搜索失败 - ${e.message}`);
        }
    }
    
    // 保存数据
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf8');
    console.log('✅ 数据已更新:', DATA_FILE);
    
    // 部署到 GitHub
    await deployToGitHub();
    
    return data;
}

// 如果直接运行此脚本
if (require.main === module) {
    update().then(() => {
        console.log('🎉 更新完成!');
        process.exit(0);
    }).catch(e => {
        console.error('❌ 更新失败:', e);
        process.exit(1);
    });
}

module.exports = { update, search };
