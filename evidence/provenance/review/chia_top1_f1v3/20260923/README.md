# F1-v3 RC-informed repair 結果

## 結論

F1-v3 的第二段 global-route RC repair 確實把 ad71 post-route delay 從 F1-v2 的 2.407488 ns 降到 **2.404520 ns**，但仍差 4.520 ps，且 J 從 1.014981857 惡化到 **1.075936547**、面積從 2414 增至 **2504 um²**。這不是可採用新解。

工具在第二段加入 14 次 resize、3 次 pin swap、1 次 clone，將 global-route proxy 最慢路徑從 input30→data_o[59] 搬到 input14→data_o[63]。proxy arrival 只改善 18.927 ps，仍有 14 個 endpoint 違反 2.35 ns optimizer target；最終 extracted critical path也維持 input14→data_o[63]。這顯示工具修復了會移動的 proxy 瓶頸，時序只得到邊際改善，能量與面積成本卻很大。

338a/F1-v1 得到 D=2.434211 ns、J=0.989879136、area=2421，雖比 F1-v2 稍省能，卻失去可行性。現階段保留 **338a/F1-v2：D=2.379898 ns、J=0.992112249、area=2434** 作可用解。

## 驗證

兩次新 route 都是 actual CHIA execution；route、全輸出等價 proof、三 profile measurement 均 PASS。共同 goal 維持 D<=2.40 ns 與 b271/F0 分母。本輪使用2個人工指定機制辨識 route，與已結束的三-route模型 episode 分開記帳。

- F1-v3 recipe SHA-256: `39806753c4dacf0473f28443df96a202358ba6ffbae7e4f7ff3d2b41424af93a`
- 338a/F1-v1 output SHA-256: `c40f559aadd89c520aaeeb1d6995039972b7350b84c436d0bb9cbc7561642f2f`
- ad71/F1-v3 output SHA-256: `4fb51f7a5fb8dddc06ca3c478cda65640fe8c6da0604d3574fb33fdb84cb5c73`

## Phase B：28b/F1-v2 energy-bound probe

28b/F1-v2 的 route、proof、三 profile measurement 均 PASS，但 D=**2.435118 ns**，仍差35.118 ps；J 從 F0 的0.980772114惡化到 **1.068151153**，面積從2412增加到 **2549 um²**。它改善395.547 ps delay，卻完全消耗最低 mapped-energy parent 的能量餘裕，因此不再原樣重試。

- 28b/F1-v2 output SHA-256: `62c6f669beff8fce873d5ad395ddc6b88e50ad95ffabf95a31f3605767454b0f`

## Phase B：338a/F1-v4 power recovery

338a/F1-v4 得到新的最佳可行點：D=**2.372445 ns**、J=**0.991374753**、area=2434 um²，主goal餘裕27.555 ps。相對F1-v2，在相同rounded area下delay再改善7.453 ps、J改善0.000737496。

recover_power實際接受2個downsizing：_317_與_329_均由inv_2換成inv_1；instance總數維持554，netlist bytes確實改變。但global-route proxy WNS與rounded area在recover前後都維持-0.195790 ns與2434 um²，因此最終收益仍與後續incremental legalization/global routing糾纏；沒有skip-recover control前，不把全部收益歸因給downsizing。

- F1-v4 recipe SHA-256: `d08ca5d15da104ec9dcc7c56e6aeee46553e4f029fa407b8d0bd99c97afbdb48`
- 338a/F1-v4 output SHA-256: `ffd27e209a701d67f34ecd787a811da3210735b720c67ae91616ab8135dea1cd`

## F1-v4 matched routing control

移除recover_power、保留相同incremental legalization/routing的control，逐數重現F1-v2：D=2.379898 ns、J=0.992112249、area=2434。這排除了單獨reroute造成新best的解釋。

相對control，兩個downsizing與其匹配reroute使D改善7.453 ps、J改善0.000737496；stress與uniform分別省0.005642360與0.000256113 pJ，low-toggle增加0.000012406 pJ。F1-v4的整體改善可歸因於recover_power接受的兩個downsizing及其後路由更新。

- control output SHA-256: `62ef6948399d026ac4cc81416b46937bfde04497689d2228be2c83f28283ab85`
