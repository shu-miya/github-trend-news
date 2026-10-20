/* Local preview ONLY. These star counts and rankings are fictional examples. */
(function(){
  const example = [
    ['vercel/next.js','The React Framework for the Web.','TypeScript','開発ツール',15420],
    ['anthropics/claude-code','AI coding assistant in your terminal.','TypeScript','AI・エージェント',8420],
    ['microsoft/vscode','Visual Studio Code open source editor.','TypeScript','開発ツール',6840],
    ['NationalSecurityAgency/ghidra','Software reverse engineering framework.','Java','セキュリティ',5180],
    ['huggingface/transformers','Models for text, vision and audio AI applications.','Python','AI・エージェント',4690],
    ['astral-sh/ruff','An extremely fast Python linter and formatter.','Rust','開発ツール',3830],
    ['facebook/react','The library for web and native user interfaces.','JavaScript','開発ツール',3320],
    ['langchain-ai/langchain','Build applications with large language models.','Python','AI・エージェント',2710],
    ['openai/openai-python','The official Python library for the OpenAI API.','Python','AI・エージェント',2150],
    ['psf/requests','A simple, yet elegant, HTTP library.','Python','開発ツール',1420]
  ];
  const intro = {
    'AI・エージェント':'AIの活用や自動化に関係するプロジェクトです。',
    'セキュリティ':'ソフトウェアの仕組みを分析するツールです。',
    '開発ツール':'プログラムの作成や開発作業を助けるプロジェクトです。'
  };
  const periods = {};
  for (const [period,factor] of [['daily',0.18],['weekly',1],['monthly',3.2]]) {
    periods[period]={source_url:`https://github.com/trending?since=${period}`, repositories:example.map((x,i)=>({rank:i+1,full_name:x[0],url:'https://github.com/'+x[0],description:x[1],language:x[2],category:x[3],intro_ja:intro[x[3]],stars_period:Math.round(x[4]*factor),stars_total:null}))};
  }
  // The following metadata is fictional and is displayed only in DEMO mode.
  const sampleDetails = [
    {stars_total:150000,forks:3500,license:'MIT',pushed_on:'2026-10-19',
      use_case_ja:'Webアプリケーションを構築するためのフレームワーク。画面表示やデータ取得の構成を整えます。',
      topics:['react','framework','web'],readme_excerpt:'Example README overview text for building web applications.',
      readme_features:['App routing and server-side functionality','Tools for interactive applications']},
    {stars_total:100000,forks:4500,license:'MIT',pushed_on:'2026-10-18',
      use_case_ja:'AIでコードを読んだり編集したりするための開発支援ツール。開発の定型作業を効率化します。',
      topics:['agent','coding'],readme_excerpt:'Example documentation for a coding assistant.',
      readme_features:['Natural language code operations','Command line workflow']},
    {stars_total:180000,forks:20000,license:'MIT',pushed_on:'2026-10-19',
      use_case_ja:'コード編集や拡張機能の利用など開発環境を整えるためのエディタです。',
      topics:['editor','typescript'],readme_excerpt:'Example documentation for an editor.',
      readme_features:['Cross-platform editing support','Extension-based customization']}
  ];
  for(const period of Object.values(periods)){
    period.repositories.slice(0,3).forEach((repo,index)=>{
      repo.details={...sampleDetails[index],source:'DEMO / invented'};
    });
  }
  window.GH_NEWS_DEMO={schema_version:1,date_jst:'2026-10-20',captured_at:'2026-10-20T03:00:00+00:00',source:'DEMO ONLY - fictional sample rankings and star counts',is_demo:true,periods};
})();
