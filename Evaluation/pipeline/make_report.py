"""Build a local, filterable score report from completed evaluation outputs."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); out=args.out
    summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
    values={}
    for metric in ('siglip2','pe'):
        values[metric]={row['sample_id']:row for row in (json.loads(line) for line in (out/f'{metric}.jsonl').read_text(encoding='utf-8').splitlines())}
    rows=[]
    for row in values['siglip2'].values():
        pe=values['pe'][row['sample_id']]
        rows.append({key:row[key] for key in ('sample_id','candidate_id','category','level','variant','caption')}
                    | {'siglip2':row['max_score'],'pe':pe['max_score'],
                       'siglip2_mean':row['mean_score'],'pe_mean':pe['mean_score'],
                       'siglip2_truncated':row['text_truncated'],'pe_truncated':pe['text_truncated'],
                       'siglip2_image':f'renders/{row["sample_id"]}/{row["best_view"]:02d}.png',
                       'pe_image':f'renders/{row["sample_id"]}/{pe["best_view"]:02d}.png'})
    template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BrickMore 模型评分</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f5f7;color:#18212f;font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}
main{max-width:1500px;margin:30px auto;padding:0 24px}h1{font-size:30px;margin-bottom:4px}.sub{color:#59677b;margin-top:0}
.cards{display:flex;gap:16px;margin:22px 0}.card{flex:1;background:white;border:1px solid #dce2ea;border-radius:10px;padding:18px}.card b{font-size:25px;display:block}.card span{color:#59677b}
.note{background:#fff8e6;border-left:4px solid #d5a024;padding:12px 16px;margin:16px 0}
.controls{display:flex;gap:10px;flex-wrap:wrap;background:white;border:1px solid #dce2ea;padding:14px;border-radius:10px;position:sticky;top:0;z-index:2}
select,input{font:inherit;padding:6px 10px;border:1px solid #b9c4d1;border-radius:5px}input{min-width:230px}.count{margin-left:auto;align-self:center;color:#59677b}
table{border-collapse:collapse;width:100%;background:white;margin-top:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #e0e6ed;vertical-align:top}th{background:#e9eef5}
.thumb{width:104px;height:104px;object-fit:contain;background:#c2c3bf;border-radius:5px}.num{font-variant-numeric:tabular-nums;font-weight:650}.caption{max-width:520px}.small{font-size:12px;color:#68778a}.tag{background:#edf1f6;padding:2px 6px;border-radius:4px}
a{color:#215ba5}.footer{color:#68778a;margin:22px 0}button{font:inherit;padding:6px 14px;border:1px solid #b9c4d1;background:white;border-radius:5px;cursor:pointer}
</style><main>
<h1>BrickMore 模型评分</h1><p class="sub">SigLIP2 Base 224 · PE-Core Base 224 · 每份 GLB 八个视角取最高分</p>
<section class="cards" id="cards"></section>
<div class="note">每个候选使用自己的原始英文提示词。候选之间的提示词不同，分数不能单独决定“最佳模型”。统一使用黄色材质；图文语义分数不表示正确率或物理稳定性。PE 的 32-token 上下文会截断较长描述。</div>
<p><a href="scores.csv">下载逐模型 CSV</a> · <a href="by_category_level.csv">类别与等级统计</a> · <a href="paired_changes.csv">配对变化</a> · <a href="REPORT.md">完整说明</a> · <a href="render_qa.png">16 类渲染预览</a></p>
<div class="controls"><select id="category"><option value="">全部类别</option></select><select id="level"><option value="">全部等级</option></select><select id="variant"><option value="">全部版本</option><option value="raw">raw 原始版</option><option value="stitched">stitched 拼接版</option></select><select id="sort"><option value="siglip2">按 SigLIP2 降序</option><option value="pe">按 PE 降序</option><option value="id">按模型编号</option></select><input id="search" placeholder="搜索模型编号或英文提示词"><span class="count" id="count"></span></div>
<table><thead><tr><th>模型</th><th>SigLIP2 最佳视角</th><th>PE 最佳视角</th><th>SigLIP2</th><th>PE</th><th>原始英文提示词</th></tr></thead><tbody id="body"></tbody></table>
<p><button id="more">加载更多</button></p><p class="footer">每次显示 60 条。图像可点击放大。所有结果与图片均保存在本地。</p>
<script>
const summary=__SUMMARY__,rows=__ROWS__;
const $=id=>document.getElementById(id);
function node(tag,text,cls){const element=document.createElement(tag);if(text!==undefined)element.textContent=text;if(cls)element.className=cls;return element}
for(const variant of ['raw','stitched']){const value=summary.overall[variant],card=node('div',undefined,'card');card.append(node('span',variant+' · '+value.count+' 份 GLB'));card.append(node('b',value.siglip2.toFixed(6)+' / '+value.pe.toFixed(6)));card.append(node('span','SigLIP2 / PE 总体均值'));$('cards').append(card)}
const paired=node('div',undefined,'card');paired.append(node('span','配对比较 · '+summary.paired_count+' 个候选'));paired.append(node('b',(summary.paired_mean_delta.siglip2>=0?'+':'')+summary.paired_mean_delta.siglip2.toFixed(6)+' / '+(summary.paired_mean_delta.pe>=0?'+':'')+summary.paired_mean_delta.pe.toFixed(6)));paired.append(node('span','stitched − raw 平均变化'));$('cards').append(paired);
for(const name of ['category','level'])for(const value of [...new Set(rows.map(row=>row[name]))].sort()){$(name).append(new Option(value,value))}
let visible=60;
function refresh(){
const query=$('search').value.toLowerCase(),sort=$('sort').value;
const filtered=rows.filter(row=>(!$('category').value||row.category===$('category').value)&&(!$('level').value||row.level===$('level').value)&&(!$('variant').value||row.variant===$('variant').value)&&(!query||(row.candidate_id+' '+row.caption).toLowerCase().includes(query)));
filtered.sort((a,b)=>sort==='id'?a.sample_id.localeCompare(b.sample_id):b[sort]-a[sort]);
$('body').replaceChildren();
for(const row of filtered.slice(0,visible)){
const tr=node('tr'),identity=node('td');identity.append(node('b',row.candidate_id),node('div',row.variant+' · '+row.level,'small'));tr.append(identity);
for(const metric of ['siglip2','pe']){const td=node('td'),link=node('a'),img=node('img');link.href=row[metric+'_image'];link.target='_blank';img.src=link.href;img.className='thumb';img.loading='lazy';img.alt=row.candidate_id+' '+metric+' 最佳视角';link.append(img);td.append(link);tr.append(td)}
for(const metric of ['siglip2','pe']){const td=node('td');td.append(node('div',row[metric].toFixed(6),'num'),node('div','八视角均值 '+row[metric+'_mean'].toFixed(6),'small'));if(row[metric+'_truncated'])td.append(node('div','提示词已截断','small'));tr.append(td)}
tr.append(node('td',row.caption,'caption'));$('body').append(tr)}
$('count').textContent=filtered.length+' 条结果';$('more').hidden=visible>=filtered.length;
}
for(const name of ['category','level','variant','sort','search'])$(name).addEventListener('input',()=>{visible=60;refresh()});$('more').onclick=()=>{visible+=60;refresh()};refresh();
</script></main></html>'''
    encoded_rows=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')
    encoded_summary=json.dumps(summary,ensure_ascii=False).replace('<','\\u003c')
    html=template.replace('__ROWS__',encoded_rows).replace('__SUMMARY__',encoded_summary)
    (out/'report.html').write_text(html,encoding='utf-8')
    report=out/'REPORT.md'
    marker='\n## 文本截断统计\n'
    original=report.read_text(encoding='utf-8').split(marker)[0]
    details=['','## 文本截断统计','',
             '| 版本 | SigLIP2 截断 | PE 截断 |','|---|---:|---:|']
    for variant in ('raw','stitched'):
        value=summary['overall'][variant]
        details.append(f'| {variant} | {value["truncated"]["siglip2"]}/{value["count"]} | {value["truncated"]["pe"]}/{value["count"]} |')
    details+=['','原始版和拼接版的可用样本不完全相同，整体均值不能直接解释为拼接前后的变化；前后变化应看 438 个候选的配对统计。',
              '','每份模型的截断标记和实际 token 数保存在 scores.csv；按等级的文本检查见 text_audit.json。']
    report.write_text(original+'\n'.join(details)+'\n',encoding='utf-8')
    print('Saved',out/'report.html')


if __name__=='__main__': main()
