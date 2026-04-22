#!/usr/bin/env node
/**
 * AI科技日报自动更新脚本
 * 定时执行搜索并更新 data.json
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PROXY_PORT = process.env.AUTH_GATEWAY_PORT || '19000';
const PROXY_HOST = '127.0.0.1';
const API_PATH = '/proxy/prosearch/search';

const DATA_FILE = path.join(__dirname, 'data.json');

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
