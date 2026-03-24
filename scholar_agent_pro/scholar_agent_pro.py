import streamlit as st
import pandas as pd
import statsmodels.api as sm
from DrissionPage import ChromiumPage, ChromiumOptions
from openai import OpenAI
import plotly.express as px
import re
import time
import random
from urllib.parse import quote as url_quote 
import requests  # 用于 OpenAlex API 请求

# ----- 一、AI提取关键词（代码已整合到AI分析与报告模块）—----
#代码见“五、AI分析与报告模块”部分

# ----- 二、 基础配置 -----
# 设置Streamlit页面配置
st.set_page_config(page_title="ScholarAgent Pro", page_icon="🎓", layout="wide")

# 期刊白名单配置 - 按语言和等级分类
# 用于后续判断文献来源的期刊等级
TARGET_JOURNALS = {
    "CN": {
        "A+": ["中国社会科学"],
        "A": ["经济研究", "管理世界"],
        "A-": ["金融研究", "经济学（季刊）", "世界经济", "中国工业经济", "统计研究", "管理科学学报"]
    },
    "EN": {
        "A+": [
            "American Economic Review", "Econometrica", "Journal of Political Economy", 
            "Quarterly Journal of Economics", "Review of Economic Studies",
            "Journal of Finance", "Journal of Financial Economics", "Review of Financial Studies",
            "Management Science"
        ],
        "A": [
            "Economic Journal", "Games and Economic Behavior", "International Economic Review", 
            "Journal of Econometrics", "Journal of Economic Theory", "Journal of European Economic Association",
            "Journal of International Economics", "Journal of Labor Economics", "Journal of Monetary Economics",
            "Journal of Public Economics", "RAND Journal of Economics", "Review of Economics and Statistics", 
            "Theoretical Economics", "Journal of Banking and Finance", "Journal of Corporate Finance",
            "Journal of Financial and Quantitative Analysis", "Journal of Money, Credit and Banking", 
            "Journal of Risk and Insurance", "Review of Finance",
            "Journal of Accounting and Economics", "Journal of Accounting Research", "The Accounting Review",
            "Information Systems Research", "Journal on Computing", "MIS Quarterly", "Operations Research",
            "Journal of Operations Management", "Manufacturing and Service Operations Management",
            "Production and Operations Management", "Academy of Management Journal", "Academy of Management Review",
            "Administrative Science Quarterly", "Organization Science", "Journal of International Business Studies",
            "Strategic Management Journal", "Journal of Consumer Research", "Journal of Marketing",
            "Journal of Marketing Research", "Marketing Science", "International Journal of Project Management"
        ],
        "A-": [
            "American Economic Journal: Applied Economics", "American Economic Journal: Economic Policy", 
            "American Economic Journal: Macroeconomics", "American Economic Journal: Microeconomics",
            "American Economic Review: Insights", "Econometric Theory", "Economic Theory", 
            "International Journal of Industrial Organization", "Journal of Development Economics", 
            "Journal of Economic Behavior and Organization", "Journal of Economic Dynamics and Control",
            "Journal of Economic Growth", "Journal of Health Economics", "Journal of Industrial Economics", 
            "Journal of Law and Economics", "Journal of Urban Economics", "Review of Economic Dynamics",
            "Financial Management", "Journal of Empirical Finance", "Journal of Financial Intermediation",
            "Journal of Financial Markets", "Journal of Financial Stability", "Journal of International Money and Finance",
            "Journal of Risk and Uncertainty", "Mathematical Finance", "Review of Asset Pricing Studies",
            "Review of Corporate Finance Studies", "Insurance: Mathematics and Economics",
            "Accounting, Organizations and Society", "Contemporary Accounting Research"
        ]
    }
}

def get_journal_tier(source_name, lang="CN"):
    """
    判断期刊等级，根据预设的期刊白名单
    
    Args:
        source_name: 期刊名称
        lang: 期刊语言（CN或EN）
    
    Returns:
        str: 期刊等级，格式为"CN-等级"或"EN-等级"，未匹配则返回"Other"
    """
    if not source_name: return "Other"
    name = source_name.strip()
    
    # 根据语言选择优先检查的期刊列表
    if lang == "CN":
        for tier, j_list in TARGET_JOURNALS["CN"].items():
            for target in j_list:
                if target in name: return f"CN-{tier}"
    
    name_lower = name.lower()
    for tier, j_list in TARGET_JOURNALS["EN"].items():
        for target in j_list:
            if target.lower() in name_lower: return f"EN-{tier}"
    return "Other"

# ----- 三、爬虫模块 -----

def scrape_detail_page(page, link, log_container):
    """
    进入文献详情页抓取摘要和关键词
    
    Args:
        page: ChromiumPage对象
        link: 详情页链接
        log_container: 日志容器
    
    Returns:
        tuple: (摘要, 关键词)
    """
    abstract = "无摘要"
    keywords = "无关键词"
    
    try:
        # 打开新标签页访问详情
        page.run_js(f"window.open('{link}', '_blank');")
        page.wait.new_tab(timeout=8)  # 减少超时时间
        tab = page.latest_tab
        
        # 检查标签页是否成功打开
        if not tab:
            return "打开失败", "打开失败"
        
        time.sleep(1)  # 减少等待时间，1秒通常够了
        
        # 检查页面标题
        try:
            page_title = tab.title
        except:
            page_title = ""
        
        # 检查是否需要验证码
        if "验证" in page_title or "滑块" in tab.html[:2000]:
            tab.close()
            page.tab_to_first()
            return "需要验证", "需要验证"
        
        # 抓取摘要：尝试多种选择器
        abstract_found = False
        try:
            # 方法1：通过ID
            elem = tab.ele('#ChDivSummary')
            if elem:
                text = elem.text.strip()
                if text and len(text) > 10:
                    abstract = text
                    abstract_found = True
            
            # 方法2：通过CSS类
            if not abstract_found:
                elem = tab.ele('css:.abstract-text')
                if elem:
                    text = elem.text.strip()
                    if text and len(text) > 10:
                        abstract = text
                        abstract_found = True
            
            # 方法3：通过文本搜索
            if not abstract_found:
                elem = tab.ele('text:摘要')
                if elem:
                    parent = elem.parent()
                    if parent:
                        text = parent.text.replace("摘要", "").replace(":", "").replace("：", "").strip()
                        if text and len(text) > 10:
                            abstract = text
                            abstract_found = True
                        
        except Exception as e:
            pass  # 静默处理摘要抓取异常
        
        # 抓取关键词：尝试多种选择器
        keywords_found = False
        try:
            # 方法1：通过 .keywords a 标签
            kws = tab.eles('css:.keywords a')
            if kws and len(kws) > 0:
                kw_list = []
                for k in kws:
                    text = k.text.strip()
                    # 过滤空文本和只包含特殊字符的文本
                    if text and len(text) > 0 and text not in [';', '；', ',', '，', ' ']:
                        kw_list.append(text)
                if kw_list:
                    keywords = "; ".join(kw_list)
                    keywords_found = True
            
            # 方法2：通过文本搜索"关键词"
            if not keywords_found:
                elem = tab.ele('text:关键词')
                if elem:
                    parent = elem.parent()
                    if parent:
                        text = parent.text.replace("关键词", "").replace(":", "").replace("：", "").strip()
                        text = " ".join(text.split())
                        if text and len(text) > 1:
                            keywords = text
                            keywords_found = True
            
            # 方法3：尝试其他关键词选择器
            if not keywords_found:
                elem = tab.ele('css:.keywords')
                if elem:
                    text = elem.text.replace("关键词", "").replace(":", "").replace("：", "").strip()
                    if text and len(text) > 1:
                        keywords = text
                        keywords_found = True
                            
        except Exception as e:
            pass  # 静默处理关键词抓取异常
        
        # 清理关键词：移除多余的分号和空格
        if keywords and keywords != "无关键词":
            # 替换常见的分隔符为统一的分号
            keywords = keywords.replace(";;", ";").replace("; ;", ";").replace(" ;", ";").replace("; ", "; ")
            # 移除开头和结尾的分号
            keywords = keywords.strip("; ").strip("；")
            # 如果清理后为空，设置默认值
            if not keywords:
                keywords = "无关键词"
        
        # 关闭详情页标签
        tab.close()
        
        # 确保切回主标签页
        try:
            page.tab_to_first()
        except:
            pass
        
        # 成功抓取，返回结果
        return abstract[:500], keywords
        
    except Exception as e:
        # 强制清理：关闭所有非主标签页
        try:
            # 获取所有标签页，只保留第一个
            all_tabs = page.tabs
            if len(all_tabs) > 1:
                for t in all_tabs[1:]:
                    try:
                        t.close()
                    except:
                        pass
        except: 
            pass
        
        # 尝试切回主标签页
        try:
            page.tab_to_first()
        except:
            pass
        
        # 返回"无"而不是"失败"，这样文章不会被跳过
        return "无摘要", "无关键词"

# --- CNKI 爬虫 (增强版：支持关键词+摘要) ---
def scrape_cnki(topic, target_count, strategy, log_container, fetch_details=True, keywords=None):
    """
    爬取中国知网(CNKI)的学术文献数据
    
    Args:
        topic: 研究主题
        target_count: 目标抓取数量
        strategy: 抓取策略（HYBRID/SC/SU）
        log_container: 日志容器
        fetch_details: 是否抓取详情页（摘要+关键词）
        keywords: 可选，用于增强搜索的关键词列表
    
    Returns:
        pd.DataFrame: 抓取的文献数据
    """
    data_list = []
    
    # 1. 定义任务队列
    tasks = []
    if strategy == 'HYBRID':
        half_count = max(5, target_count // 2)
        tasks = [('SU', half_count), ('SC', target_count - half_count)]
    else:
        tasks = [(strategy, target_count)]

    # 2. 配置浏览器
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    co.set_argument('--ignore-certificate-errors')
    # 尝试使用隐身模式，防止缓存（如果知网验证码太频繁，可注释掉这一行）
    # co.incognito(True) 
    
    page = None
    try:
        # 尝试接管或新建浏览器
        page = ChromiumPage(co)
        log_container.info("🚀 正在启动浏览器... (如果卡住请手动关闭旧的 Chrome 窗口)")
        
        # 3. 访问搜索页
        # 优先使用关键词搜索，如果没有关键词则使用原始主题
        if keywords:
            # 只使用AI提取的关键词进行搜索
            combined_topic = " ".join(keywords)
        else:
            # 如果没有关键词，则使用原始主题
            combined_topic = topic
        safe_topic = url_quote(combined_topic)
        base_url = f'https://kns.cnki.net/kns8/defaultresult/index?kw={safe_topic}'
        page.get(base_url)
        
        # --- 辅助函数 ---
        def wait_for_table(timeout_seconds):
            end_time = time.time() + timeout_seconds
            while time.time() < end_time:
                # 检查多种可能的表格结构
                if page.ele('.wq-list-table'): return True
                if page.ele('.result-table-list'): return True
                if page.ele('css:tbody tr'): return True
                time.sleep(1)
            return False

        # --- 智能等待与验证 ---
        log_container.info("⏳ 正在等待搜索结果加载...")
        if not wait_for_table(5):
            log_container.warning("⚠️ 未检测到数据表格，可能触发了知网滑块验证！")
            log_container.error("👉 请立即切换到浏览器窗口，手动完成滑块验证！程序将在 60秒 内持续检测...")
            if not wait_for_table(60):
                log_container.error("❌ 超时：验证未通过或页面加载失败。")
                try: page.quit()
                except: pass
                return pd.DataFrame(data_list)
            else:
                log_container.success("✅ 验证通过！")

        time.sleep(2) # 等待页面稳定

        # 4. 遍历任务
        for sort_type, task_limit in tasks:
            # === 核心修复：更稳健的排序切换逻辑 ===
            if sort_type == 'SC':
                sort_name = "按被引排序(经典)"
                # 尝试多种选择器
                sort_btn = page.ele('css:.sort-cite') or page.ele('text:被引')
                if sort_btn:
                    log_container.info(f"🖱️ 正在切换到【被引排序】...")
                    # 使用 js 点击更稳定
                    sort_btn.click(by_js=True)
                    time.sleep(3) # 等待页面刷新
                    if not wait_for_table(10):
                        log_container.error("❌ 切换排序后表格加载失败，跳过此策略")
                        continue
                    time.sleep(1)  # 确保DOM稳定
                    log_container.success("✅ 排序切换成功")
                else:
                    log_container.warning("⚠️ 未找到被引排序按钮，继续使用当前排序")
            
            elif sort_type == 'SU':
                sort_name = "按相关度排序(最新)"
                # 尝试找"主题"或者"相关度"
                sort_btn = page.ele('css:.sort-default') or page.ele('text:相关度')
                
                # 只有当按钮存在且没有被激活（通常激活状态会有特定class，这里简单处理直接点）时才点
                if sort_btn:
                    log_container.info(f"🖱️ 正在切换到【主题排序】...")
                    sort_btn.click(by_js=True)
                    time.sleep(3) # 等待页面刷新
                    if not wait_for_table(10):
                        log_container.error("❌ 切换排序后表格加载失败，跳过此策略")
                        continue
                    time.sleep(1)  # 确保DOM稳定
                    log_container.success("✅ 排序切换成功")
            else:
                sort_name = "默认排序"
            
            log_container.info(f"🔄 当前策略: {sort_name}，目标抓取: {task_limit} 条")

            current_task_count = 0
            page_num = 1
            
            # --- 每一页的循环 ---
            while current_task_count < task_limit:
                # 快速确认表格存在（不等待，因为上面已经验证过了）
                if not (page.ele('.wq-list-table') or page.ele('.result-table-list') or page.ele('css:tbody tr')):
                    log_container.warning("⚠️ 表格不存在，尝试等待...")
                    wait_for_table(5)
                
                # 获取数据行
                rows = page.eles('.wq-list-table tr') or page.eles('.result-table-list tr') or page.eles('css:tbody tr')
                
                if not rows:
                    # 有时候翻页后数据还没来，再等一下
                    time.sleep(2)
                    rows = page.eles('.wq-list-table tr') or page.eles('css:tbody tr')
                    if not rows:
                        break 

                for row in rows:
                    if current_task_count >= task_limit: break
                    try:
                        # 提取标题
                        title_ele = row.ele('.name') or row.ele('.fz14')
                        if not title_ele: continue
                        title = title_ele.text.strip()

                        # 去重检查
                        if any(d['Title'] == title for d in data_list): continue

                        # 获取详情页链接 - 尝试多种选择器
                        link = None
                        link_ele = None
                        
                        # 尝试多种选择器
                        if not link_ele:
                            link_ele = row.ele('.name a')
                        if not link_ele:
                            link_ele = row.ele('css:.fz14 a')
                        if not link_ele:
                            link_ele = row.ele('css:a')  # 任意链接
                        if not link_ele:
                            # 从标题元素的父元素中找链接
                            if title_ele:
                                link_ele = title_ele.ele('tag:a')
                        
                        if link_ele:
                            link = link_ele.attr('href')

                        # 提取其他字段
                        source_ele = row.ele('.source') or row.ele('css:td:nth-child(3)')
                        source = source_ele.text.strip() if source_ele else "未知来源"
                        
                        date_ele = row.ele('.date') or row.ele('css:td:nth-child(4)')
                        date_text = date_ele.text.strip() if date_ele else ""
                        year_match = re.search(r'(19|20)\d{2}', date_text)
                        year = int(year_match.group()) if year_match else None
                        
                        quote_ele = row.ele('.quote') or row.ele('css:td:nth-child(5)')
                        quote_text = quote_ele.text if quote_ele else "0"
                        citation_count = int(quote_text) if quote_text.isdigit() else 0
                        
                        # 【新增】抓取详情页的摘要和关键词
                        abstract = "未抓取摘要"
                        keywords = "未抓取关键词"
                        skip_this_article = False  # 标记是否跳过本文
                        
                        if fetch_details and link:
                            try:
                                abstract, keywords = scrape_detail_page(page, link, log_container)
                            except Exception as e:
                                # 强制清理标签页
                                try:
                                    all_tabs = page.tabs
                                    if len(all_tabs) > 1:
                                        for t in all_tabs[1:]:
                                            try: t.close()
                                            except: pass
                                    page.tab_to_first()
                                except:
                                    pass
                            
                            time.sleep(random.uniform(0.3, 0.8))  # 减少随机延迟
                        
                        # 如果标记为跳过，则不添加到结果中，继续下一篇
                        if skip_this_article:
                            continue
                        
                        if year:
                            tier = get_journal_tier(source, "CN")
                            data_list.append({
                                "Title": title,
                                "Source": source,
                                "Year": year,
                                "Citations": citation_count,
                                "Keywords": keywords,
                                "Abstract": abstract,
                                "Tier": tier,
                                "Strategy": sort_name,
                                "Language": "CN"
                            })
                            current_task_count += 1
                    except Exception:
                        continue
                
                log_container.info(f"📄 {sort_name}: 第 {page_num} 页抓取完毕，本轮进度: {current_task_count}/{task_limit}")
                
                # 翻页逻辑
                if current_task_count < task_limit:
                    try:
                        next_btn = page.ele('#PageNext')
                        if next_btn:
                            # 检查是否到了最后一页 (disabled)
                            if 'disabled' in next_btn.attr('class') or next_btn.style('display') == 'none':
                                log_container.info("已到达最后一页")
                                break
                            
                            # 滚动到底部防止被遮挡
                            page.scroll.to_bottom()
                            next_btn.click(by_js=True) # 使用 JS 点击翻页更稳
                            time.sleep(2) # 翻页等待
                            page_num += 1
                        else:
                            break
                    except Exception:
                        break
        
        log_container.success(f"🎉 CNKI 抓取完成！共收集 {len(data_list)} 条中文数据。")
        # 任务完成后关闭浏览器，防止影响下一次任务
        try: page.quit()
        except: pass
        
        return pd.DataFrame(data_list)

    except Exception as e:
        log_container.error(f"❌ 发生程序错误: {str(e)}")
        # 出错也要尝试关闭浏览器
        try: 
            if page: page.quit()
        except: pass
        return pd.DataFrame(data_list)


# --- OpenAlex 爬虫 (英文文献) - 支持关键词！ --- 
def scrape_openalex(topic, target_count, log_container, keywords=None):
    """
    使用 OpenAlex API 爬取英文文献
    
    Args:
        topic: 研究主题
        target_count: 目标抓取数量
        log_container: 日志容器
        keywords: 可选，用于增强搜索的关键词列表
    
    Returns:
        pd.DataFrame: 抓取的文献数据
    """
    data_list = []
    # 优先使用关键词搜索，如果没有关键词则使用原始主题
    if keywords:
        # 只使用AI提取的关键词进行搜索
        combined_topic = " ".join(keywords)
    else:
        # 如果没有关键词，则使用原始主题
        combined_topic = topic
    log_container.info(f"🌍 [OpenAlex] 启动检索: {combined_topic}")
    
    # OpenAlex API 文档: https://docs.openalex.org/
    api_url = "https://api.openalex.org/works"
    
    # 添加礼貌邮箱可获得更好的请求速率（无需注册）
    polite_email = "scholar_agent@example.com"
    
    page = 1
    per_page = 25  # OpenAlex 每页最多 200，但我们用小批量
    
    while len(data_list) < target_count:
        params = {
            "search": combined_topic,
            "per_page": min(per_page, target_count - len(data_list)),
            "page": page,
            "mailto": polite_email,  # 礼貌请求，获得更好速率
            # 按被引次数排序，获取高质量文献
            "sort": "cited_by_count:desc"
        }
        
        try:
            # OpenAlex 对礼貌请求限制很宽松，但仍建议适当间隔
            time.sleep(1)
            r = requests.get(api_url, params=params, timeout=20)
            
            if r.status_code != 200:
                log_container.warning(f"⚠️ OpenAlex API 返回 {r.status_code}，跳过剩余部分。")
                break
            
            data = r.json()
            results = data.get("results", [])
            if not results:
                log_container.info("已无更多结果")
                break
            
            for p in results:
                title = p.get("title")
                if not title:
                    continue
                
                # 去重检查
                if any(d['Title'] == title for d in data_list):
                    continue
                
                # 获取来源期刊
                primary_location = p.get("primary_location") or {}
                source_info = primary_location.get("source") or {}
                venue = source_info.get("display_name") or "Unknown"
                
                year = p.get("publication_year")
                
                # 【核心】提取关键词 - OpenAlex 返回 keywords 数组
                keywords_list = p.get("keywords", [])
                if keywords_list:
                    # 每个 keyword 是 {"id": "...", "display_name": "xxx", "score": 0.xx}
                    keywords = "; ".join([
                        kw.get("display_name", "") 
                        for kw in keywords_list[:8]  # 最多取8个关键词
                        if kw.get("display_name")
                    ])
                else:
                    keywords = "N/A"
                
                # 提取摘要（OpenAlex 返回倒排索引格式，需要重构）
                abstract = "No Abstract"
                abstract_inverted = p.get("abstract_inverted_index")
                if abstract_inverted:
                    try:
                        # 重构摘要文本
                        word_positions = []
                        for word, positions in abstract_inverted.items():
                            for pos in positions:
                                word_positions.append((pos, word))
                        word_positions.sort(key=lambda x: x[0])
                        abstract = " ".join([w for _, w in word_positions])[:500]
                    except:
                        abstract = "摘要解析失败"
                
                if year:
                    data_list.append({
                        "Title": title,
                        "Source": venue,
                        "Year": year,
                        "Citations": p.get("cited_by_count", 0),
                        "Keywords": keywords,  # ✅ OpenAlex 支持关键词！
                        "Abstract": abstract,
                        "Tier": get_journal_tier(venue, "EN"),
                        "Strategy": "OpenAlex",
                        "Language": "EN"
                    })
                    
                    if len(data_list) >= target_count:
                        break
            
            page += 1
            log_container.info(f"  -> OpenAlex 已获取 {len(data_list)} 条英文文献...")
            
            # 检查是否已获取所有可用结果
            meta = data.get("meta", {})
            total_count = meta.get("count", 0)
            if page * per_page >= total_count:
                log_container.info("已获取所有可用结果")
                break
            
        except requests.exceptions.Timeout:
            log_container.warning("⚠️ OpenAlex API 请求超时，跳过剩余部分。")
            break
        except Exception as e:
            log_container.error(f"OpenAlex 网络错误: {e}")
            break
    
    log_container.success(f"🎉 OpenAlex 抓取完成！共收集 {len(data_list)} 条英文数据（含关键词）。")
    return pd.DataFrame(data_list)


# ----- 四、计量分析模块 -----  
def run_analytics(df):
    """
    时间-文献数量趋势回归分析
    
    Args:
        df: 文献数据DataFrame
    
    Returns:
        dict: 回归分析结果，包含误差信息、回归指标和图表数据
    """
    if df.empty: return None
    trend = df.groupby('Year').size().reset_index(name='Count')
    if df['Year'].nunique() < 2:
        return {
            "error": True,
            "msg": f"⚠️ 数据年份过于集中（仅 {df['Year'].unique()[0]} 年），无法回归。",
            "chart_data": trend
        }
    X = sm.add_constant(trend['Year'])
    try:
        model = sm.OLS(trend['Count'], X).fit()
        last_year = trend['Year'].max()
        future_years = [last_year + i for i in range(1, 6)]  # 预测未来5年
        const = model.params['const']
        slope = model.params['Year']
        predictions = [const + slope * y for y in future_years]
        future_df = pd.DataFrame({'Year': future_years, 'Count': predictions, 'Type': '预测'})
        trend['Type'] = '历史'
        combined = pd.concat([trend, future_df])
        
        # 提取更多回归指标
        r_squared = model.rsquared
        p_values = model.pvalues
        std_err = model.bse
        
        # 回归方程字符串
        regression_eq = f"Count = {const:.2f} + {slope:.2f} × Year"
        
        return {
            "error": False, 
            "r_squared": r_squared,
            "p_value": p_values['Year'],
            "std_err": std_err['Year'],
            "slope": slope,
            "const": const,
            "regression_eq": regression_eq,
            "chart_data": combined,
            "actual_data": trend
        }
    except Exception as e:
         return {"error": True, "msg": f"回归分析失败: {str(e)}", "chart_data": trend}


def keyword_citation_regression(df):
    """
    关键词-被引数相关性回归分析
    以关键词出现频率为自变量，文献被引次数为因变量
    
    Args:
        df: 文献数据DataFrame，包含关键词和被引次数
    
    Returns:
        dict: 回归分析结果，包含误差信息、回归指标和分析数据
    """
    if df.empty: return None
    
    # 1. 提取所有关键词并统计频率
    all_keywords = []
    if 'Keywords' in df.columns:
        for kw_str in df['Keywords'].dropna():
            if kw_str and kw_str not in ["未抓取", "未抓取关键词", "N/A"]:
                # 分割关键词（可能用 ; 或 、 分隔）
                keywords = re.split(r'[;；,，、]', kw_str)
                for kw in keywords:
                    kw = kw.strip()
                    if kw and len(kw) > 1:  # 过滤空关键词和单字符关键词
                        all_keywords.append(kw)
    
    if not all_keywords:
        return {
            "error": True,
            "msg": "⚠️ 未提取到有效关键词，无法进行相关性分析。"
        }
    
    # 2. 统计关键词频率
    kw_counts = pd.Series(all_keywords).value_counts().reset_index()
    kw_counts.columns = ['Keyword', 'Frequency']
    
    # 3. 构建关键词-被引次数数据集
    kw_citation_data = []
    for idx, row in df.iterrows():
        if pd.isna(row['Keywords']) or row['Keywords'] in ["未抓取", "未抓取关键词", "N/A"]:
            continue
        
        # 分割当前文献的关键词
        paper_keywords = re.split(r'[;；,，、]', row['Keywords'])
        for kw in paper_keywords:
            kw = kw.strip()
            if kw and len(kw) > 1:
                # 查找该关键词的频率
                freq = kw_counts[kw_counts['Keyword'] == kw]['Frequency'].values
                if len(freq) > 0:
                    kw_citation_data.append({
                        'Keyword': kw,
                        'Frequency': freq[0],
                        'Citations': row['Citations']
                    })
    
    if not kw_citation_data:
        return {
            "error": True,
            "msg": "⚠️ 关键词数据不足，无法进行相关性分析。"
        }
    
    # 4. 构建回归模型
    kw_citation_df = pd.DataFrame(kw_citation_data)
    
    # 过滤掉出现频率过低的关键词（至少出现3次）
    kw_citation_df = kw_citation_df.groupby('Keyword').filter(lambda x: len(x) >= 3)
    
    if len(kw_citation_df) < 5:  # 至少需要5个样本
        return {
            "error": True,
            "msg": "⚠️ 有效样本数不足，无法进行相关性分析。"
        }
    
    X = sm.add_constant(kw_citation_df['Frequency'])
    y = kw_citation_df['Citations']
    
    try:
        # 5. 拟合线性回归模型
        model = sm.OLS(y, X).fit()
        
        # 提取回归指标
        r_squared = model.rsquared
        p_values = model.pvalues
        slope = model.params['Frequency']
        const = model.params['const']
        
        # 回归方程
        regression_eq = f"Citations = {const:.2f} + {slope:.2f} × Frequency"
        
        return {
            "error": False,
            "r_squared": r_squared,
            "p_value": p_values['Frequency'],
            "slope": slope,
            "const": const,
            "regression_eq": regression_eq,
            "data": kw_citation_df
        }
    except Exception as e:
        return {
            "error": True,
            "msg": f"相关性回归失败: {str(e)}"
        }

# ----- 五、AI分析与报告模块 ----- 

def analyze_keywords(topic, api_key, base_url, language="zh"):
    """
    使用LLM分析研究主题，提取相关关键词
    
    Args:
        topic: 研究主题
        api_key: DeepSeek API Key
        base_url: API基础URL
        language: 主题语言（zh或en）
    
    Returns:
        list: 提取的关键词列表（恰好5个关键词）
    """
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        if language == "zh":
            prompt = f"""请分析以下研究主题，精确提取出5个最相关的核心关键词，
            只返回关键词，用分号分隔，不要添加任何其他说明：
            {topic}
            """
        else:
            prompt = f"""Please analyze the following research topic and extract exactly 5 most relevant core keywords,
            only return the keywords separated by semicolons, no other explanations:
            {topic}
            """
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages= [{"role": "user", "content": prompt}],
            temperature=0.1  # 降低温度以获得更一致的输出
        )
        
        keywords_str = response.choices[0].message.content.strip()
        # 尝试多种分隔符来处理AI可能使用的不同格式
        import re
        # 匹配分号、逗号、换行符或其他常见分隔符
        keywords = re.split(r'[;\n,|，；\t]+', keywords_str)
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        
        # 确保返回恰好5个关键词
        if len(keywords) >= 5:
            keywords = keywords[:5]  # 取前5个
        elif len(keywords) == 0:
            # 如果没有提取到关键词，返回默认关键词
            keywords = ["研究主题", "数据分析", "学术论文", "趋势分析", "文献综述"]
        else:
            # 如果少于5个，补充默认关键词直到达到5个
            default_additions = ["研究主题", "数据分析", "学术论文", "趋势分析", "文献综述"]
            while len(keywords) < 5:
                # 使用默认关键词补充，避免重复使用最后的关键词
                additional_keyword = default_additions[(len(keywords)) % len(default_additions)]
                # 添加序号以避免完全重复
                if additional_keyword in keywords:
                    additional_keyword = f"{additional_keyword}_{len(keywords)}"
                keywords.append(additional_keyword)
        
        return keywords
    except Exception as e:
        print(f"关键词分析失败: {e}")
        # 返回默认的5个关键词
        return ["研究主题", "数据分析", "学术论文", "趋势分析", "文献综述"]


def translate_keywords(keywords, target_lang="en", api_key=None, base_url=None):
    """
    将关键词翻译成目标语言
    
    Args:
        keywords: 关键词列表
        target_lang: 目标语言（en或zh）
        api_key: DeepSeek API Key
        base_url: API基础URL
    
    Returns:
        list: 翻译后的关键词列表
    """
    if not keywords:
        return []
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        keywords_str = "; ".join(keywords)
        
        if target_lang == "en":
            prompt = f"请将以下中文关键词翻译成英文，保持原意，只返回翻译结果，用分号分隔：\n{keywords_str}"
        else:
            prompt = f"Please translate the following English keywords into Chinese, keep the original meaning, only return the translation results separated by semicolons:\n{keywords_str}"
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages= [{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        translated_str = response.choices[0].message.content.strip()
        translated_keywords = [kw.strip() for kw in translated_str.split(";") if kw.strip()]
        return translated_keywords
    except Exception as e:
        print(f"关键词翻译失败: {e}")
        return keywords


def generate_mindmap(topic, df, time_regression_res=None, kw_regression_res=None):
    """
    生成HTML格式的思维导图
    输出可直接在浏览器中打开的HTML文件
    """
    if df.empty: 
        return f"<!DOCTYPE html>\n<html lang='zh-CN'>\n<head>\n<meta charset='UTF-8'>\n<title>思维导图 - {topic}</title>\n</head>\n<body>\n<h1>无法生成思维导图，数据为空</h1>\n</body>\n</html>"
    
    # 1. 提取基本信息
    min_year = df['Year'].min()
    max_year = df['Year'].max()
    total_papers = len(df)
    
    # 2. 提取关键词（前15个）
    all_keywords = []
    if 'Keywords' in df.columns:
        for kw_str in df['Keywords'].dropna():
            if kw_str and kw_str not in ["未抓取", "未抓取关键词", "N/A"]:
                keywords = re.split(r'[;；,，、]', kw_str)
                for kw in keywords:
                    kw = kw.strip()
                    if kw and len(kw) > 1:
                        all_keywords.append(kw)
    
    top_keywords = []
    if all_keywords:
        kw_counts = pd.Series(all_keywords).value_counts()
        top_keywords = kw_counts.head(15).index.tolist()
    
    # 3. 提取高被引文献（前10个）
    high_cited = df.nlargest(10, 'Citations')
    high_cited_titles = high_cited['Title'].tolist()
    
    # 4. 生成HTML思维导图
    # 使用三引号字符串，避免f-string转义问题
    mindmap_template = '''<!DOCTYPE html>
<html lang='zh-CN'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>思维导图 - {topic}</title>
    <style>
        * {{margin: 0; padding: 0; box-sizing: border-box;}}
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 2px solid #3498db;
        }}
        .mindmap {{
            margin: 20px 0;
        }}
        ul {{
            list-style-type: none;
            padding-left: 20px;
        }}
        li {{
            margin: 10px 0;
            position: relative;
        }}
        li::before {{
            content: '▶';
            color: #3498db;
            margin-right: 8px;
            font-size: 12px;
        }}
        li.collapsible {{
            cursor: pointer;
        }}
        li.collapsible::before {{
            content: '▼';
        }}
        li.collapsible.collapsed::before {{
            content: '▶';
        }}
        .collapsible-content {{
            display: block;
        }}
        .collapsible-content.collapsed {{
            display: none;
        }}
        .section-title {{
            font-weight: bold;
            color: #2c3e50;
            margin: 15px 0 10px 0;
            font-size: 18px;
        }}
        .subsection-title {{
            font-weight: bold;
            color: #3498db;
            margin: 10px 0 5px 0;
            font-size: 16px;
        }}
        .content-item {{
            margin-left: 20px;
        }}
        .highlight {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .note {{
            font-style: italic;
            color: #7f8c8d;
            margin-left: 20px;
        }}
        /* 添加折叠/展开功能的CSS */
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
                padding: 15px;
            }}
            ul {{
                padding-left: 15px;
            }}
        }}
    </style>
    <script>
        // 添加折叠/展开功能
        document.addEventListener('DOMContentLoaded', function() {{
            const collapsibles = document.querySelectorAll('.collapsible');
            collapsibles.forEach(item => {{
                item.addEventListener('click', function() {{
                    this.classList.toggle('collapsed');
                    const content = this.nextElementSibling;
                    if (content && content.classList.contains('collapsible-content')) {{
                        content.classList.toggle('collapsed');
                    }}
                }});
            }});
        }});
    </script>
</head>
<body>
    <div class='container'>
        <h1>{topic}</h1>
        <div class='mindmap'>
            <ul>
                <li class='collapsible section-title'>研究概况</li>
                <ul class='collapsible-content'>
                    <li>文献数量: <span class='highlight'>{total_papers}篇</span></li>
                    <li>年份跨度: <span class='highlight'>{min_year}-{max_year}</span></li>
                </ul>
                
                <li class='collapsible section-title'>时间分布</li>
                <ul class='collapsible-content'>
                    {time_distribution_content}
                </ul>
                
                <li class='collapsible section-title'>核心关键词</li>
                <ul class='collapsible-content'>
                    {keywords_html}
                </ul>
                
                <li class='collapsible section-title'>高被引文献</li>
                <ul class='collapsible-content'>
                    {high_cited_html}
                </ul>
                
                <li class='collapsible section-title'>回归分析结论</li>
                <ul class='collapsible-content'>
                    {time_regression_content}
                    {kw_regression_content}
                </ul>
            </ul>
        </div>
    </div>
</body>
</html>'''    
    
    # 构建回归分析结论的HTML
    time_regression_html = """
                    <li class='subsection-title'>时间-文献数量回归</li>
                    <ul>
                        <li>回归方程: {regression_eq}</li>
                        <li>R²: {r_squared:.3f}</li>
                        <li>P值: {p_value:.4f}</li>
                        <li>趋势: {trend}</li>
                    </ul>"""
    
    kw_regression_html = """
                    <li class='subsection-title'>关键词-被引数回归</li>
                    <ul>
                        <li>回归方程: {regression_eq}</li>
                        <li>R²: {r_squared:.3f}</li>
                        <li>P值: {p_value:.4f}</li>
                        <li>结论: {conclusion}</li>
                    </ul>"""
    
    # 生成时间回归部分的HTML
    time_regression_content = ""
    if time_regression_res and not time_regression_res.get("error"):
        time_regression_content = time_regression_html.format(
            regression_eq=time_regression_res['regression_eq'],
            r_squared=time_regression_res['r_squared'],
            p_value=time_regression_res['p_value'],
            trend="研究热度呈上升趋势" if time_regression_res['slope'] > 0 else "研究热度呈下降趋势"
        )
    
    # 生成关键词回归部分的HTML
    kw_regression_content = ""
    if kw_regression_res and not kw_regression_res.get("error"):
        kw_regression_content = kw_regression_html.format(
            regression_eq=kw_regression_res['regression_eq'],
            r_squared=kw_regression_res['r_squared'],
            p_value=kw_regression_res['p_value'],
            conclusion="关键词频率与被引次数正相关" if kw_regression_res['slope'] > 0 else "关键词频率与被引次数负相关"
        )
    
    # 生成时间分布部分的HTML
    time_distribution_content = f"""
                    <li>最早发表: {min_year}年</li>
                    <li>最新发表: {max_year}年</li>"""
    if time_regression_res and not time_regression_res.get("error"):
        time_distribution_content += f"""
                    <li>回归方程: {time_regression_res['regression_eq']}</li>
                    <li>拟合优度(R²): {time_regression_res['r_squared']:.3f}</li>"""
    
    # 生成关键词列表的HTML
    keywords_html = "".join([f"<li>{kw}</li>" for kw in top_keywords[:10]])
    if len(top_keywords) > 10:
        keywords_html += f"<li class='note'>等{len(top_keywords) - 10}个关键词</li>"
    
    # 生成高被引文献列表的HTML
    high_cited_html = "".join([f"<li>{title[:50]}...</li>" for title in high_cited_titles[:5]])
    if len(high_cited_titles) > 5:
        high_cited_html += f"<li class='note'>等{len(high_cited_titles) - 5}篇文献</li>"
    
    # 组装完整的HTML
    mindmap = mindmap_template.format(
        topic=topic,
        total_papers=total_papers,
        min_year=min_year,
        max_year=max_year,
        time_distribution_content=time_distribution_content,
        keywords_html=keywords_html,
        high_cited_html=high_cited_html,
        time_regression_content=time_regression_content,
        kw_regression_content=kw_regression_content
    )
    return mindmap


def generate_ai_report(df, topic_cn, topic_en, api_key, base_url):
    """
    生成 AI 智能综述报告
    【增强版】支持中英文文献，利用关键词信息，基于实际回归结果生成分析
    
    Args:
        df: 文献数据DataFrame
        topic_cn: 中文研究主题
        topic_en: 英文研究主题
        api_key: DeepSeek API Key
        base_url: API基础URL
    
    Returns:
        tuple: (流式响应对象或错误字符串, 思维导图Markdown文本)
    """
    if not api_key:
        return "❌ 请在左侧侧边栏输入 DeepSeek API Key"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        min_year = df['Year'].min()
        max_year = df['Year'].max()
        avg_citation = df['Citations'].mean()
        total_papers = len(df)
        
        # 统计中英文文献数量
        cn_count = len(df[df['Language'] == 'CN']) if 'Language' in df.columns else len(df)
        en_count = len(df[df['Language'] == 'EN']) if 'Language' in df.columns else 0
        
        # 统计期刊分布（前8个）
        top_journals = df['Source'].value_counts().head(8).to_dict()
        
        # 【新增】提取高频关键词（前15个）
        top_keywords = "未提取"
        keyword_counts = {}  # 用于存储关键词计数
        if 'Keywords' in df.columns:
            all_keywords = []
            for kw in df['Keywords'].dropna():
                if kw and kw not in ["未抓取", "未抓取关键词", "N/A"]:
                    for k in re.split(r'[;；,，、]', str(kw)):
                        k = k.strip()
                        if k and len(k) > 1:
                            all_keywords.append(k)
            if all_keywords:
                kw_counts = pd.Series(all_keywords).value_counts().head(15)
                top_keywords = ", ".join([f"{k}({v})" for k, v in kw_counts.items()])
                keyword_counts = kw_counts.to_dict()
        
        # 【新增】高被引文献（前10个）
        high_cited = df.nlargest(10, 'Citations')
        high_cited_summaries = []
        for _, row in high_cited.iterrows():
            summary = {
                "title": row['Title'],
                "year": row['Year'],
                "citations": row['Citations'],
                "source": row['Source'],
                "abstract": row.get('Abstract', '无摘要')
            }
            high_cited_summaries.append(summary)
        
        # 【新增】提取按关键词分类的文献摘要
        keyword_abstracts = {}
        if 'Keywords' in df.columns and 'Abstract' in df.columns:
            for kw in top_keywords.split(', ')[:5]:  # 取前5个关键词
                if kw and '(' in kw:
                    keyword = kw.split('(')[0].strip()
                    keyword_abstracts[keyword] = []
                    
                    # 查找包含该关键词的文献
                    for idx, row in df.iterrows():
                        if pd.notna(row['Keywords']) and keyword in row['Keywords'] and pd.notna(row['Abstract']):
                            keyword_abstracts[keyword].append({
                                "title": row['Title'],
                                "abstract": row['Abstract'][:200]  # 只取摘要前200字
                            })
                    
                    # 每个关键词最多保留5篇文献的摘要
                    keyword_abstracts[keyword] = keyword_abstracts[keyword][:5]
        
        # 【新增】时间分布特征
        year_counts = df['Year'].value_counts().sort_index()
        year_distribution = "\n".join([f"{year}: {count}篇" for year, count in year_counts.items()])
        
        # 运行回归分析
        time_regression_res = run_analytics(df)
        kw_regression_res = keyword_citation_regression(df)
        
        # 生成思维导图
        mindmap = generate_mindmap(topic_cn, df, time_regression_res, kw_regression_res)
        
        # 准备回归分析结果文本
        regression_results_text = ""
        
        # 时间-文献数量回归结果
        if time_regression_res and not time_regression_res.get("error"):
            regression_results_text += f"""
            ## 时间-文献数量回归分析
            - 回归方程: {time_regression_res['regression_eq']}
            - 拟合优度(R²): {time_regression_res['r_squared']:.3f}
            - 显著性水平(P值): {time_regression_res['p_value']:.4f}
            - 斜率: {time_regression_res['slope']:.2f}
            - 截距: {time_regression_res['const']:.2f}
            """
        else:
            regression_results_text += "\n## 时间-文献数量回归分析\n- 无法进行回归分析（数据不足或其他原因）"
        
        # 关键词-被引数回归结果
        if kw_regression_res and not kw_regression_res.get("error"):
            regression_results_text += f"""
            
            ## 关键词-被引数相关性回归分析
            - 回归方程: {kw_regression_res['regression_eq']}
            - 拟合优度(R²): {kw_regression_res['r_squared']:.3f}
            - 显著性水平(P值): {kw_regression_res['p_value']:.4f}
            - 斜率: {kw_regression_res['slope']:.2f}
            - 截距: {kw_regression_res['const']:.2f}
            """
        else:
            regression_results_text += "\n\n## 关键词-被引数相关性回归分析\n- 无法进行回归分析（数据不足或其他原因）"
        
        prompt = f"""
        请根据以下中英文学术文献数据写一份学术综述报告。
        
        ## 数据摘要
        - 主题：中文「{topic_cn}」/ 英文「{topic_en}」
        - 文献数：共 {total_papers} 篇 (中文 {cn_count}, 英文 {en_count})
        - 年份跨度：{min_year}-{max_year}，平均被引：{avg_citation:.1f}
        
        ## 主要期刊来源
        {top_journals}
        
        ## 高频关键词（出现次数）
        {top_keywords}
        
        ## 高被引文献（前10篇，含摘要）
        {high_cited_summaries}
        
        ## 按关键词分类的文献摘要（前5个关键词，每个关键词最多5篇文献）
        {keyword_abstracts}
        
        ## 文献年份分布
        {year_distribution}
        
        {regression_results_text}
        
        ## 严格要求：
        1. 生成一份结构化的学术综述报告，包含以下模块：
           - 领域研究背景
           - 核心研究方向梳理（按关键词分类）
           - 文献发表时间分布特征
           - 高被引文献核心结论总结（基于摘要内容）
           - 回归分析揭示的研究趋势（仅在有有效回归结果时包含此部分）
        2. 请严格基于提供的数据进行分析，**绝对不要虚构任何信息或数据**
        3. 对于回归分析部分，**仅基于上述提供的回归结果**进行分析，
           - 如果提供了回归结果，详细解释回归方程的含义、拟合优度和显著性
           - 如果未提供有效回归结果（显示"无法进行回归分析"），则完全跳过回归分析部分，
             不要提及任何回归相关内容
        4. 请充分利用提供的文献摘要信息，特别是高被引文献的摘要，深入分析该领域的研究内容和结论
        5. 对于核心研究方向，结合按关键词分类的文献摘要，总结每个方向的主要研究内容和观点
        6. 语言需简洁规范，符合学术综述逻辑
        7. 突出该领域的研究热点和发展趋势
        8. 最后添加生成的思维导图（使用Markdown格式）
        """
        
        # 返回流式响应对象
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        return response, mindmap

    except Exception as e:
        # 发生错误直接返回字符串
        return f"❌ API 请求失败: {str(e)}", None

# ----- 六、主界面设计 -----
def main():
    # 初始化会话状态
    if 'cn_keywords' not in st.session_state:
        st.session_state.cn_keywords = []
    if 'en_keywords' not in st.session_state:
        st.session_state.en_keywords = []
    
    st.sidebar.title("🛠️ 参数设置")
    
    # 【修改】用户输入研究问题或描述（一段话）
    st.sidebar.subheader("📚 研究问题描述")
    research_description = st.sidebar.text_area(
        "请输入您的研究问题或描述（支持中英文）",
        "我想研究数字经济对经济增长的影响，特别是在金融领域的应用和发展趋势",
        height=100
    )
    
    # 【修改】关键词分析功能
    st.sidebar.subheader("🔍 关键词分析")
    api_key = st.sidebar.text_input("DeepSeek API Key", type="password")
    api_base = st.sidebar.text_input("API Base URL", "https://api.deepseek.com")
    
    if st.button("📝 从描述中提取关键词"):
        if not api_key:
            st.sidebar.error("请先输入 DeepSeek API Key")
        elif not research_description.strip():
            st.sidebar.error("请先输入研究问题描述")
        else:
            with st.spinner("正在从描述中提取关键词..."):
                # 1. 从用户输入的描述中提取中文关键词
                cn_keywords = analyze_keywords(research_description, api_key, api_base, language="zh")
                st.session_state.cn_keywords = cn_keywords
                
                # 2. 自动翻译为英文关键词
                en_keywords = translate_keywords(cn_keywords, "en", api_key, api_base)
                st.session_state.en_keywords = en_keywords
                
                # 3. 显示提取结果
                st.sidebar.success("✅ 关键词提取完成！")
    
    # 【新增】显示和编辑关键词
    if st.session_state.cn_keywords:
        editable_cn_kw = st.sidebar.text_area("中文关键词 (可编辑)", "; ".join(st.session_state.cn_keywords), height=80)
        st.session_state.cn_keywords = [kw.strip() for kw in editable_cn_kw.split(";") if kw.strip()]
    
    if st.session_state.en_keywords:
        editable_en_kw = st.sidebar.text_area("英文关键词 (可编辑)", "; ".join(st.session_state.en_keywords), height=80)
        st.session_state.en_keywords = [kw.strip() for kw in editable_en_kw.split(";") if kw.strip()]
    
    st.sidebar.subheader("📊 抓取设置")
    count = st.sidebar.number_input("每个数据源抓取数量", 5, 100, 15)
    fetch_details = st.sidebar.checkbox("抓取详情页 (摘要+关键词)", True, help="开启后会进入每篇文章详情页抓取，速度较慢但数据更全")
    
    st.sidebar.subheader("🕷️ CNKI 抓取策略")
    strategy_map = {
        "⚖️ 混合均衡模式 (推荐)": "HYBRID",
        "🔥 高被引优先 (经典文献)": "SC",
        "🆕 相关度优先 (最新文献)": "SU"
    }
    selected_strategy_label = st.sidebar.radio("选择模式", list(strategy_map.keys()), index=0)
    strategy = strategy_map[selected_strategy_label]
    
    # 【新增】数据源选择
    st.sidebar.subheader("🌐 数据源选择")
    use_cnki = st.sidebar.checkbox("中文文献 (CNKI)", True)
    use_ss = st.sidebar.checkbox("英文文献 (OpenAlex)", True)
    
    filter_core = st.sidebar.checkbox("仅分析核心期刊", True)
    
    st.title("🎓 ScholarAgent Pro (中英文文献+关键词增强版)")

    if 'df' not in st.session_state: st.session_state.df = None

    tab1, tab2, tab3 = st.tabs(["🕷️ 数据抓取", "📈 计量分析", "🤖 智能综述"])

    with tab1:
        log_container = st.empty()
        if st.button("🚀 开始自动抓取", type="primary"):
            all_data = []
            
            # 从研究描述中提取主题关键词作为默认主题
            default_topic = research_description[:30] + "..." if len(research_description) > 30 else research_description
            
            # 【新增】中文文献抓取
            if use_cnki and research_description.strip():
                log_container.info("📖 开始抓取中文文献 (CNKI)...")
                # 使用分析出的中文关键词增强搜索
                df_cn = scrape_cnki(default_topic, count, strategy, log_container, fetch_details, 
                                   keywords=st.session_state.cn_keywords)
                if not df_cn.empty:
                    all_data.append(df_cn)
            
            # 【更新】英文文献抓取 - 使用 OpenAlex（支持关键词）
            if use_ss and research_description.strip():
                log_container.info("📖 开始抓取英文文献 (OpenAlex)...")
                # 使用分析出的英文关键词增强搜索
                df_en = scrape_openalex(default_topic, count, log_container, 
                                       keywords=st.session_state.en_keywords)
                if not df_en.empty:
                    all_data.append(df_en)
            
            # 合并数据
            if all_data:
                df = pd.concat(all_data, ignore_index=True)
                st.session_state.df = df
                
                # 统计信息
                cn_count = len(df[df['Language'] == 'CN']) if 'Language' in df.columns else 0
                en_count = len(df[df['Language'] == 'EN']) if 'Language' in df.columns else 0
                st.success(f"✅ 抓取完成！共 {len(df)} 条 (中文: {cn_count}, 英文: {en_count})")
            else:
                st.error("❌ 未抓取到任何数据，请检查网络或关键词。")
        
        if st.session_state.df is not None:
            # 【新增】按语言分组显示图表
            df_display = st.session_state.df
            if 'Language' in df_display.columns:
                fig = px.histogram(df_display, x='Year', color='Language', barmode='group', 
                                   title="文献年份分布 (按语言)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.bar_chart(df_display['Year'].value_counts().sort_index())
            
            # 【新增】显示关键词统计
            if 'Keywords' in df_display.columns:
                st.subheader("🔑 关键词概览")
                # 收集所有关键词
                all_keywords = []
                for kw in df_display['Keywords'].dropna():
                    if kw and kw not in ["未抓取", "未抓取关键词", "N/A (API不支持)"]:
                        # 分割关键词（可能用 ; 或 、 分隔）
                        for k in re.split(r'[;；,，、]', str(kw)):
                            k = k.strip()
                            if k:
                                all_keywords.append(k)
                if all_keywords:
                    kw_counts = pd.Series(all_keywords).value_counts().head(20)
                    st.bar_chart(kw_counts)
            
            # 数据表格
            st.subheader("📊 详细数据")
            st.dataframe(df_display, use_container_width=True)

    with tab2:
        if st.session_state.df is not None:
            df_view = st.session_state.df.copy()
            if filter_core: df_view = df_view[df_view['Tier'] != 'Other']
            
            st.subheader("📅 时间-文献数量回归分析")
            res = run_analytics(df_view)
            if res:
                if res.get("error"):
                    st.warning(res["msg"])
                    st.plotly_chart(px.bar(res['chart_data'], x='Year', y='Count', title="年份分布"))
                else:
                    # 显示回归指标
                    col1, col2, col3 = st.columns(3)
                    col1.metric("R²", f"{res['r_squared']:.3f}")
                    col2.metric("P值", f"{res['p_value']:.4f}")
                    col3.metric("斜率", f"{res['slope']:.2f}")
                    
                    # 生成散点图+回归线
                    fig = px.scatter(
                        res['actual_data'], 
                        x='Year', 
                        y='Count', 
                        title=f"时间-文献数量回归分析\n{res['regression_eq']}",
                        labels={'Year': '发表年份', 'Count': '文献数量'},
                        trendline="ols",
                        trendline_scope="overall"
                    )
                    
                    # 添加预测数据
                    fig.add_scatter(
                        x=res['chart_data'][res['chart_data']['Type'] == '预测']['Year'],
                        y=res['chart_data'][res['chart_data']['Type'] == '预测']['Count'],
                        mode='lines+markers',
                        name='预测值',
                        line=dict(dash='dash')
                    )
                    
                    # 添加指标注释
                    fig.add_annotation(
                        x=0.5,
                        y=-0.2,
                        xref="paper",
                        yref="paper",
                        text=f"R² = {res['r_squared']:.3f}, P值 = {res['p_value']:.4f}",
                        showarrow=False,
                        font=dict(size=12)
                    )
                    
                    st.plotly_chart(fig)
            else: 
                st.warning("数据为空")
            
            st.divider()
            
            # 关键词-被引数相关性回归分析
            st.subheader("🔑 关键词-被引数相关性回归分析")
            kw_res = keyword_citation_regression(df_view)
            if kw_res:
                if kw_res.get("error"):
                    st.warning(kw_res["msg"])
                else:
                    # 显示回归指标
                    col1, col2, col3 = st.columns(3)
                    col1.metric("R²", f"{kw_res['r_squared']:.3f}")
                    col2.metric("P值", f"{kw_res['p_value']:.4f}")
                    col3.metric("斜率", f"{kw_res['slope']:.2f}")
                    
                    # 生成散点图+回归线
                    fig2 = px.scatter(
                        kw_res['data'], 
                        x='Frequency', 
                        y='Citations', 
                        title=f"关键词频率-被引次数相关性\n{kw_res['regression_eq']}",
                        labels={'Frequency': '关键词出现频率', 'Citations': '文献被引次数'},
                        trendline="ols",
                        trendline_scope="overall"
                    )
                    
                    # 添加指标注释
                    fig2.add_annotation(
                        x=0.5,
                        y=-0.2,
                        xref="paper",
                        yref="paper",
                        text=f"R² = {kw_res['r_squared']:.3f}, P值 = {kw_res['p_value']:.4f}",
                        showarrow=False,
                        font=dict(size=12)
                    )
                    
                    st.plotly_chart(fig2)
                    
                    # 显示高影响力关键词
                    st.subheader("💡 高影响力关键词分析")
                    # 计算每个关键词的平均被引次数
                    kw_avg_citation = kw_res['data'].groupby('Keyword').agg({
                        'Citations': 'mean',
                        'Frequency': 'first'
                    }).reset_index()
                    kw_avg_citation = kw_avg_citation.sort_values('Citations', ascending=False).head(10)
                    st.bar_chart(kw_avg_citation.set_index('Keyword')[['Citations', 'Frequency']])
            else:
                st.warning("数据为空")

    with tab3:
        # 确保只有在有数据时才显示按钮
        if st.session_state.df is not None:
            if st.button("🤖 生成智能综述报告", type="primary"):
                # 添加 spinner 让用户知道程序在运行
                with st.spinner("🤖 正在连接大模型生成报告，请稍候..."):
                    # 从研究描述或关键词中生成主题
                    report_topic_cn = research_description[:50] + "..." if len(research_description) > 50 else research_description
                    # 生成英文主题（简单处理，实际应用中可使用翻译API）
                    report_topic_en = "Research on " + report_topic_cn[:30] + "..." if len(report_topic_cn) > 30 else "Research on " + report_topic_cn
                    result, mindmap = generate_ai_report(st.session_state.df, report_topic_cn, report_topic_en, api_key, api_base)
                    
                # 简单的类型判断
                if isinstance(result, str):
                    # 如果返回的是字符串，说明出错了
                    st.error(result)
                else:
                    # 如果不是字符串，说明是Stream对象
                    box = st.empty()
                    txt = ""
                    try:
                        for chunk in result:
                            # 兼容 DeepSeek 返回可能存在的 None content
                            delta = chunk.choices[0].delta
                            if hasattr(delta, 'content') and delta.content:
                                txt += delta.content
                                box.markdown(txt)
                        
                        # 显示思维导图
                        st.divider()
                        st.subheader("🧠 研究领域思维导图")
                        
                        # 显示HTML思维导图
                        st.components.v1.html(mindmap, height=600, scrolling=True)
                        
                        # 添加下载按钮
                        st.download_button(
                            label="📥 下载思维导图（HTML格式）",
                            data=mindmap,
                            file_name=f"{report_topic_cn}_思维导图.html",
                            mime="text/html"
                        )
                        
                    except Exception as e:
                        st.error(f"流式传输中断: {e}")
        else:
            st.info("👈 请先在第一个标签页抓取数据")

if __name__ == "__main__":
    main()