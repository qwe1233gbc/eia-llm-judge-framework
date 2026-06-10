Table
<table><tr><td> Strategy</td><td> Advantages</td><td> Disadvantages</td><td>Applicable scenarios</td><td>Cost</td></tr><tr><td>Fine-Tuning</td><td>Modest increases in accuracy and stability,while fast response</td><td>Less flexible when objectives change]</td><td>Rule-driven,standardized,fast-response tasks (e.g., compliance checking, pollutant classification）</td><td>High (Requires extensive data curation and expert labor）</td></tr><tr><td>Agentic Workflows</td><td>Flexible,real-time, cross-domain collaboration</td><td>Engineering complexity and quality depends on tool chain and prompts</td><td>Time-sensitive and data-intensive tasks requiring retrieval, computation,and verification (e.g., risk screening using calculators,data-pipeline tasks of integrating multisource data)</td><td>Low-Moderate (Costs depend on tool integration and maintenance by experts)</td></tr><tr><td>Model Updates</td><td>Strong reasoning ability and adaptability</td><td>Lower precision in specific domains</td><td>Large-scale,interdisciplinary decision tasks (e.g.,scenario planning,cross-domain evidence integration for strategy design)</td><td>Low (Faster deployment with fewer data- specific adjustments)</td></tr></table>

practice, shared cases (e.g., environmental scenarios across multiple Chinese provinces from this train data set) can be incorporated jointly and then combined with region-specific rules to adapt models for local regulatory contexts, reducing downstream curation effort while maintaining consistency. Importantly, the data set construction and validation methodology is itself reusable, allowing the same structured abstraction and expert-in-the-loop process to be applied when generating task-specific or region-specific training data under different environmental decision contexts.

Furthermore, agentic workflows are better built on the most up-to-date, high-capability generalist backbone models, which provide strong cross-domain reasoning and robustness to novel situations. By coupling these models with retrieval, computation, and verification tools, agentic systems can support timesensitive, data-intensive, and interdisciplinary environmental decisions, such as policy analysis, impact forecasting, and adaptive management, without incurring the high upfront costs of domain-specific retraining. Importantly, fine-tuned models can be selectively incorporated within agentic workflows as verification or checking components, for example to validate regulatory interpretations, numerical outputs, or domainspecific constraints, thereby improving reliability without sacrificing overall system flexibility. While agentic workflows may not always match the precision of fine-tuned models on narrowly defined tasks, their modular integration enables targeted precision where it matters most.

From a practical perspective, these findings support a layered deployment approach: selectively fine-tune models for stable, high-frequency core tasks and for verification roles within agentic systems, while relying on agentic workflows anchored in state-of-the-art foundation models for complex, evolving decision-making. This division of roles aligns domain precision with adaptive intelligence, supporting scalable, transparent, and resilient environmental decision systems.

## 4.7. Limitations and Future Work

This study has several limitations. First, the data set shows a strong geographic and linguistic bias, with 95% of materials sourced from Chinese-authored textbooks. While this captures China-specific environmental management logic, it limits exposure to global frameworks; future work will incorporate multilingual, cross-regional, and policy-diverse sources to improve generalizability. Second, although the textbookderived corpus spans multiple environmental subdomains, it masks how individual source types influence model performance. Comparative analyses using disciplinary, policy-oriented, or mixed corpora are needed to disentangle the effects of data diversity from corpus scale. Third, the 328-question test set, though designed to maximize representativeness across subfields and reasoning dimensions, remains moderate in size. Broader and more internationally calibrated benchmarks, with greater expert participation, are required to enhance statistical robustness. Moreover, static Q&A formats cannot fully represent dynamic environmental tasks such as spatial analysis, time-series forecasting, or multicriteria decisionmaking; future benchmarks should therefore integrate spatiotemporal and scenario-based evaluations. Fourth, while subdomain-specific fine-tuning (e.g., soil, air, water) may improve within-domain accuracy, environmental decisionmaking often requires cross-domain reasoning. Hierarchical architecture that combines a general environmental foundation with specialized expert modules may better balance adaptability and precision. Fifth, all evaluated models rely on compact backbones (∼7−8B parameters), reducing scalerelated confounding but limiting examination of capacity effects. Because reasoning performance may correlate with parameter count, future studies should benchmark models across multiple sizes and architectures to isolate the influences of scale, design, and fine-tuning strategy. Finally, methodological and scalability challenges remain. Subtle evaluator biases may persist despite high inter-rater agreement, and the current agentic workflow could benefit from parallelized tool invocation, dynamic load-balance, and expert-rule integration to improve throughput and reliability in production-scale applications.

## ■ ASSOCIATED CONTENT

## \*sı Supporting Information

The Supporting Information is available free of charge at https://pubs.acs.org/doi/10.1021/acs.est.5c09526.

1. Textbook coverages 2. Training data validation 3. Testing data 4. Evaluation prompt 5. Statistical validation methods and results 6. Representative response comparisons between models 7. Representative error cases and model response analysis 8. Fleiss’ kappa for all three- and four-rater combinations (PDF)

## ■ AUTHOR INFORMATION

## Corresponding Authors

Nan Li − School of Environment, Tsinghua University, Beijing 100084, P. R. China; State Key Laboratory of Iron and Steel Industry Environmental Protection, School of Environment, Tsinghua University, Beijing 100084, P.R. China; Email: linan@tsinghua.edu.cn

Ming Xu − School of Environment, Tsinghua University, Beijing 100084, P. R. China; State Key Laboratory of Iron and Steel Industry Environmental Protection, School of Environment, Tsinghua University, Beijing 100084, P.R. China; Email: xu-ming@tsinghua.edu.cn

## Authors

Chuke Chen − School of Environment, Tsinghua University, Beijing 100084, P. R. China

Jianchuan Qi − School of Environment, Tsinghua University, Beijing 100084, P. R. China; orcid.org/0000-0001-7026- 2442

Huimin Chang − School of Environment, Tsinghua University, Beijing 100084, P. R. China

Wenjie Shi − School of Environment, Tsinghua University, Beijing 100084, P. R. China

Jinliang Xie − School of Environment, Tsinghua University, Beijing 100084, P. R. China

Jiayi Yuan − School of Environment, Tsinghua University, Beijing 100084, P. R. China

Hang Yang − School of Environment, Tsinghua University, Beijing 100084, P. R. China

Jing Guo − School of Management Science and Engineering, Beijing Information Science & Technology University, Beijing 102206, P. R. China

Changqing Xu − School of Economics, Beijing Institute of Technology, Beijing 100081, P. R. China

Complete contact information is available at: https://pubs.acs.org/10.1021/acs.est.5c09526

Notes

The authors declare no competing financial interest.

## ACKNOWLEDGMENTS

This work was supported by National Key Research and Development Program (Grant No. 2023YFE0122400), National Natural Science Foundation of China (Grant No. 52430004, 52293445), Tsinghua University (2024SM279), and Amazon Research Award, ARA. This work is also supported by the TianGong Initiative (https://www. tiangong.earth), which provided rules, guidance, tools, and technical support.

## ABBREVIATIONS

GAI, Generative artificial intelligence; LLMs, Large language models; LCA, Life cycle assessment; RAG, Retrievalaugmented generation; SOTA, State-of-the-art; CI, Confidence intervals; KDE, Kernel density estimation

## REFERENCES

(1) Cash, D.; Adger, W. N.; Berkes, F.; Garden, P.; Lebel, L.; Olsson, P.; Pritchard, L.; Young, O. Scale and Cross-Scale Dynamics: Governance and Information in a Multilevel World. Ecol. Soc. 2006, 11 (2), 1.

(2) Zhang, Q.; Eckelman, M. J.; Fu, G.; Liang, S.; Mihelcic, J. R.; Mo, W.; Zimmerman, J. B. Systems Approaches for Addressing Complex Environmental Problems. Environ. Sci. Technol. 2024, 58 (43), 19093−19094.

(3) Ostrom, E. A General Framework for Analyzing Sustainability of Social-Ecological Systems. Science 2009, 325 (5939), 419−422.

(4) Policy Change And Learning: an Advocacy Coalition Approach; Sabatier, P. A.; Jenkins-Smith, H. C., Eds.; Westview Press: Boulder, Colo, 1993.

(5) Lu, M.; Gao, F.; Tang, X.; Chen, L. Analysis and Prediction in SCR Experiments Using GPT-4 with an Effective Chain-of-Thought Prompting Strategy. iScience 2024, 27 (4), 109451.

(6) Zhong, S.; Guan, X. Developing Quantitative Structure−Activity Relationship (QSAR) Models for Water Contaminants’ Activities/ Properties by Fine-Tuning GPT-3 Models. Environ. Sci. Technol. Lett. 2023, 10 (10), 872−877.

(7) Liang, W.; Su, W.; Zhong, L.; Yang, Z.; Li, T.; Liang, Y.; Ruan, T.; Jiang, G. Comprehensive Characterization of Oxidative Stress-Modulating Chemicals Using GPT-Based Text Mining. Environ. Sci. Technol. 2024, 58 (46), 20540−20552.

(8) Zheng, Z.; Zhang, O.; Borgs, C.; Chayes, J. T.; Yaghi, O. M. ChatGPT Chemistry Assistant for Text Mining and the Prediction of MOF Synthesis. J. Am. Chem. Soc. 2023, 145 (32), 18048−18062.

(9) Qiu, Y.; Mintenig, S.; Barchiesi, M.; Koelmans, A. A. Using Artificial Intelligence Tools for Data Quality Evaluation in the Context of Microplastic Human Health Risk Assessments. Environ. Int. 2025, 197, 109341.

(10) Balaji, B.; Ebrahimi, F.; Domingo, N. G. G.; Vunnava, V. S. G.; Faridee, A.-Z.; Ramalingam, S.; Gupta, S.; Wang, A.; Gupta, H.; Belcastro, D.; et al. Emission Factor Recommendation for Life Cycle Assessments with Generative AI. Environ. Sci. Technol. 2025, 59 (18), 9113−9122.

(11) Luo, B.; Liu, J.; Deng, Z.; Yuan, C.; Yang, Q.; Xiao, L.; Xie, Y.; Zhou, F.; Zhou, W.; Liu, Z. AutoPCF: A Novel Automatic Product Carbon Footprint Estimation Framework Based on Large Language Models. Proc. AAAI Symp. Ser. 2024, 2 (1), 102−106.

(12) Chen, C.; Li, S.-L.; So, A. D.; Xu, Y.-Y.; Guo, Z.-F.; Wang, X.; Graham, D. W.; Zhu, Y.-G. Using Large Language Models to Assist Antimicrobial Resistance Policy Development: Integrating the Environment into Health Protection Planning. Environ. Sci. Technol. 2025, 59 (2), 1243−1252.

(13) Zhu, J.-J.; Jiang, J.; Yang, M.; Ren, Z. J. ChatGPT and Environmental Research. Environ. Sci. Technol. 2023, 57 (46), 17667− 17670.

(14) Wu, Y.; Xu, M.; Liu, S. Generative Artificial Intelligence: A New Engine for Advancing Environmental Science and Engineering. Environ. Sci. Technol. 2024, 58 (40), 17524−17528.

(15) Zheng, H.; Shen, L.; Tang, A.; Luo, Y.; Hu, H.; Du, B.; Wen, Y.; Tao, D. Learning from Models beyond Fine-Tuning. Nat. Mach. Intell. 2025, 7 (1), 6−17.

(16) Xu, B.; Li, Z.; Yang, Y.; Wu, G.; Wang, C.; Tang, X.; Li, Y.; Wu, Z.; Su, Q.; Shi, X.; Yang, Y.; Tong, R.; Wen, L.; Ng, H. Y. Evaluating and Advancing Large Language Models for Water Knowledge Tasks in Engineering and Research. Environ. Sci. Technol. Lett. 2025, 12 (3), 289−296.

(17) Bi, Z.; Zhang, N.; Xue, Y.; Ou, Y.; Ji, D.; Zheng, G.; Chen, H. OceanGPT: A Large Language Model for Ocean Science Tasks. arXiv, 2024, .

(18) Zhang, Y.; Lin, S.; Xiong, Y.; Li, N.; Zhong, L.; Ding, L.; Hu, Q. Fine-Tuning Large Language Models for Interdisciplinary Environmental Challenges. Environ. Sci. Ecotechnology 2025, 27, 100608.

(19) Brown, T. B.; Mann, B.; Ryder, N.; Subbiah, M.; Kaplan, J.; Dhariwal, P.; Neelakantan, A.; Shyam, P.; Sastry, G.; Askell, A.. et al.Language Models Are Few-Shot Learners. arXiv2020, .

(20) Vaghefi, S. A.; Stammbach, D.; Muccione, V.; Bingler, J.; Ni, J.; Kraus, M.; Allen, S.; Colesanti-Senni, C.; Wekhof, T.; Schimanski, T.; Gostlow, G.; Yu, T.; Wang, Q.; Webersinke, N.; Huggel, C.; Leippold, M. ChatClimate: Grounding Conversational AI in Climate Science. Commun. Earth Environ. 2023, 4 (1), 480.

(21) Webersinke, N.; Kraus, M.; Bingler, J. A.; Leippold, M. ClimateBert: A Pretrained Language Model for Climate-Related Text. arXiv2022, .

(22) Zhu, J.-J.; Yang, M.; Jiang, J.; Bai, Y.; Chen, D.; Ren, Z. J. Enabling GPTs for Expert-Level Environmental Engineering Question Answering. Environ. Sci. Technol. Lett. 2024, 11 (12), 1327−1333.

(23) Gunasekar, S.; Zhang, Y.; Aneja, J.; Mendes, C. C. T.; Giorno, A. D.; Gopi, S.; Javaheripi, M.; Kauffmann, P.; Rosa, G. D.; Saarikivi, O.; Salim, A.; Shah, S.; Behl, H. S.; Wang, X.; Bubeck, S.; Eldan, R.; Kalai, A. T.; Lee, Y. T.; Li, Y. Textbooks Are All You Need. arXiv2023, .

(24) Wang, Y.; Shen, T.; Liu, L.; Xie, J. S. Simple yet Effective Agent Framework for Complex Real-World Reasoning. arXiv2024, .

(25) Crawford, N.; Duffy, E. B.; Evazzade, I.; Foehr, T.; Robbins, G.; Saha, D. K.; Varma, J.; Ziolkowski, M. BMW Agents − A Framework For Task Automation Through Multi-Agent Collaboration. arXiv2024, .

(26) Wang, Y.; Li, X.; Wang, B.; Zhou, Y.; Lin, Y.; Ji, H.; Chen, H.; Zhang, J.; Yu, F.; Zhao, Z.; Jin, S.; Gong, R.; Xu, W. PEER: Expertizing Domain-Specific Tasks with a Multi-Agent Framework and Tuning Methods. arXiv2024, .

(27) Pal, S.; Bhattacharya, M.; Islam, M.; Chakraborty, A. C. ChatGPT or LLM in Next-Generation Drug Discovery and Development: Pharmaceutical and Biotechnology Companies Can Make Use of the Artificial Intelligence-Based Device for a Faster Way o f D r u g D i s c o v e r y a n d D e v e l o p m e n t . I n t . J . Surg.20231091243824384.

(28) Rosser, M.; Carmichael, M. G. Two Heads Are Better Than One: Collaborative LLM Embodied Agents for Human-Robot Interaction. arXiv2024, .

(29) Shah, D.; Osinski, B.; Ichter, B.; Levine, S. LM-Nav: Robotic Navigation with Large Pre-Trained Models of Language, Vision, and Action. arXiv2022, .

(30) Schmidgall, S.; Su, Y.; Wang, Z.; Sun, X.; Wu, J.; Yu, X.; Liu, J.; Liu, Z.; Barsoum, E. Agent Laboratory: Using LLM Agents as Research Assistants. arXiv2025, .

(31) Agarwal, S.; Sahu, G.; Puri, A.; Laradji, I. H.; Dvijotham, K. D.; Stanley, J.; Charlin, L.; Pal, C. L. LLMs for Literature Review: Are We There Yet?. arXiv2025, .

(32) Li, N., Linancn/TianGong-AI-Unstructure; 2025. https://github. com/linancn/TianGong-AI-Unstructure.

(33) Guo, J.; Li, N.; Xu, M. Environmental Large Language Model Evaluation (ELLE) Dataset: A Benchmark for Evaluating Generative AI Applications in Eco-Environment Domain. arXiv2025, .

(34) Li, N. Tiangong-ai-langgraph-server/src/data_synthesize_agent.ts at main · linancn/tiangong-ai-langgraph-server; 2019, https://github. com/linancn/tiangong-ai-langgraph-server/blob/main/src/data_ synthesize_agent.ts.

(35) Chen, C.; Li, N.; Qi, J.; Chang, H.; Shi, W.; Xie, J.; Yuan, J.; Yang, H.; Guo, J.; Xu, M. TianGong_Env (Revision Cdaac9f); 2025.

(36) Pareja, A.; Nayak, N. S.; Wang, H.; Killamsetty, K.; Sudalairaj, S.; Zhao, W.; Han, S.; Bhandwaldar, A.; Xu, G.; Xu, K.; Han, L.; Inglis, L.; Srivastava, A. Unveiling the Secret Recipe: A Guide For Supervised Fine-Tuning Small LLMs. arXiv2024, .

(37) Marek, M.; Lotfi, S.; Somasundaram, A.; Wilson, A. G.; Goldblum, M. Small Batch Size Training for Language Models: When Vanilla SGD Works, and Why Gradient Accumulation Is Wasteful. arXiv2025, .

(38) Microsoft, Customize a model with Azure OpenAI in Azure AI Foundry Models - Azure OpenAI; 2025, https://learn.microsoft.com/ en-us/azure/ai-foundry/openai/how-to/fine-tuning.

(39) Alrashed, S. S. Higher Learning Rate to Batch Size Ratios Can Lead to Better Reasoning in SLMs. arXiv2024, .

(40) Li, S.; Zhao, P.; Zhang, H.; Sun, X.; Wu, H.; Jiao, D.; Wang, W.; Liu, C.; Fang, Z.; Xue, J.; Tao, Y.; Cui, B.; Wang, D. Surge Phenomenon in Optimal Learning Rate and Batch Size Scaling. arXiv2024, .

(41) Li, N., Linancn/Tiangong-Ai-Langgraph-Server, 2025. https:// github.com/linancn/tiangong-ai-langgraph-server.

(42) Yao, S.; Zhao, J.; Yu, D.; Du, N.; Shafran, I.; Narasimhan, K. R.; Cao, Y. ReAct: Synergizing Reasoning and Acting in Language Models. In The 11th international conference on learning representations; ICLR, 2022.

(43) LangGraph: Multi-Agent workflows; Langchain Blog, https:// blog.langchain.com/langgraph-multi-agent-workflows/

(44) Ghafarollahi, A.; Buehler, M. J. Sparks: Multi-Agent Artificial Intelligence Model Discovers Protein Design Principles. arXiv2025, .

(45) Ghafarollahi, A.; Buehler, M. J. ProtAgents: Protein Discovery via Large Language Model Multi-Agent Collaborations Combining Physics and Machine Learning. Digital Discovery 2024, 3 (7), 1389− 1409.

(46) Wang, X.; Wei, J.; Schuurmans, D.; Le, Q.; Chi, E.; Narang, S.; Chowdhery, A.; Zhou, D. Self-Consistency Improves Chain of Thought Reasoning in Language Models. arXiv2023, .

(47) Shinn, N.; Cassano, F.; Berman, E.; Gopinath, A.; Narasimhan, K.; Yao, S. R. Language Agents with Verbal Reinforcement Learning. arXiv2023, .

(48) Abacha, A. B.; Yim, W.; Fu, Y.; Sun, Z.; Yetisgen, M.; Xia, F.; Lin, T. MEDEC: A Benchmark for Medical Error Detection and Correction in Clinical Notes. arXiv2025, .

(49) GPT-4.1 mini − OpenAI’s Lightweight Transformer Model for Developers - ChatGPT; 2025, https://gpt-gate.chat/models/gpt-4-1- mini/.

(50) ChatGPT 4.1 mini; 2025, https://amigochat.io/gpt-4-1-mini.

(51) OpenAI. Introducing GPT-4.1 in the API; 2025, https://openai. com/index/gpt-4-1/.

(52) tiangong-ai-langgraph-server/src/multi_agents/elle_evaluate.ts at main · chukeaa/tiangong-ai-langgraph-server; 2025, https://github. com/chukeaa/tiangong-ai-langgraph-server/blob/main/src/multi_ agents/elle_evaluate.ts.

(53) Landis, J. R.; Koch, G. G. The Measurement of Observer Agreement for Categorical Data. Biometrics 1977, 33 (1), 159−174.

(54) Zou, Y.; Shi, M.; Chen, Z.; Deng, Z.; Lei, Z.; Zeng, Z.; Yang, S.; Tong, H.; Xiao, L.; Zhou, W. ESGReveal: An LLM-Based Approach for Extracting Structured Data from ESG Reports. J. Cleaner Prod. 2025, 489, 144572.

(55) Meyur, R.; Phan, H.; Hayashi, K.; Stewart, I.; Sharma, S.; Chaturvedi, S.; Parker, M.; Nally, D.; Montgomery, S.; Pazdernik, K.; Jannesari, A.; Halappanavar, M.; Munikoti, S.; Horawalavithana, S.;

Acharya, A. Benchmarking LLMs for Environmental Review and Permitting. arXiv2025, .

(56) Bommasani, R.; Hudson, D. A.; Adeli, E.; Altman, R.; Arora, S.; von Arx, S.; Bernstein, M. S.; Bohg, J.; Bosselut, A.; Brunskill, E.. et al.On the Opportunities and Risks of Foundation Models. arXiv2022, .

(57) Wang, B.; Fang, H.; Eisner, J.; Durme, B. V.; Su, Y. LLMs in the Imaginarium: Tool Learning through Simulated Trial and Error. arXiv2024, .

(58) Qin, Y.; Liang, S.; Ye, Y.; Zhu, K.; Yan, L.; Lu, Y.; Lin, Y.; Cong, X.; Tang, X.; Qian, B.; Zhao, S.et al. ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs. arXiv, 2024, .

(59) Lu, W.; Luu, R. K.; Buehler, M. J. Fine-Tuning Large Language Models for Domain Adaptation: Exploration of Training Strategies, Scaling, Model Merging and Synergistic Capabilities. Npj Comput. Mater. 2025, 11 (1), 84.

(60) Zhang, G.; Xu, Z.; Jin, Q.; Chen, F.; Fang, Y.; Liu, Y.; Rousseau, J. F.; Xu, Z.; Lu, Z.; Weng, C.; Peng, Y. Leveraging Long Context in Retrieval Augmented Language Models for Medical Question Answering. Npj Digital Med. 2025, 8 (1), 1−11.

(61) Chen, C.; Luo, B.; Li, N.; Wang, B.; Yang, H.; Guo, J.; Xu, M. Spec-Driven AI for Science: The ARIA Framework for Automated and Reproducible Data Analysis. arXiv, 2025, .

(62) Li, Q.; Cui, L.; Kong, L.; Bi, W. Exploring the Reliability of Large Language Models as Customized Evaluators for Diverse NLP Tasks. arXiv, 2025, .

(63) Lee, N.; Hong, J.; Thorne, J. Evaluating the Consistency of LLM Evaluators. arXiv, 2024, .

(64) Buehler, M. J. PRefLexOR: Preference-Based Recursive Language Modeling for Exploratory Optimization of Reasoning and Agentic Thinking. Npj Artif. Intell. 2025, 1 (1), 4.

<!-- image-->

CAS BIOFINDER DISCOVERY PLATFORMTM PRECISIONDATA FOR FASTER DRUG DISCOVERY

CAS BioFinder helps you identify targets,biomarkers,andpathways

Unlock insights