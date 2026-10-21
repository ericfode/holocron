'use strict';
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto'),{isDeepStrictEqual}=require('node:util');
const engine=path.join(__dirname,'../../../forceteki');
const sha=b=>createHash('sha256').update(b).digest('hex');
let RazorCrest, FullOfSurprises, RegisteredRazor, RegisteredSurprises, RegisteredShield, RegisteredExperience, RegisteredWeakness, BuyTime, Helgait, RegisteredHelgait, Advantage, RegisteredAdvantage, FrameworkCardAbilityStep, CreateTokenUnitSystem, CardPhaseLastingEffectSystem;
function loadEngineTypes() {
Helgait=require(path.join(engine,'build/server/game/cards/08_ASH/units/HelgaitDookuWasAVisionary')).default;
Advantage=require(path.join(engine,'build/server/game/cards/08_ASH/tokens/Advantage')).default;
const registered=require(path.join(engine,'build/server/game/cards/Index')).cards;
RazorCrest=require(path.join(engine,'build/server/game/cards/08_ASH/units/RazorCrestOutfittedArmament')).default;
FullOfSurprises=require(path.join(engine,'build/server/game/cards/08_ASH/events/FullOfSurprises')).default;
RegisteredRazor=registered.get(razorProfile.id);RegisteredSurprises=registered.get(surprisesProfile.id);
RegisteredShield=registered.get(shieldProfile.id);RegisteredExperience=registered.get(experienceProfile.id);RegisteredWeakness=registered.get(weaknessProfile.id);
RegisteredHelgait=registered.get(helgaitProfile.id);RegisteredAdvantage=registered.get(advantageProfile.id);
BuyTime=require(path.join(engine,'build/server/game/cards/08_ASH/events/BuyTime')).default;
({FrameworkCardAbilityStep}=require(path.join(engine,'build/server/game/core/ability/CardAbilityStep')));
({CreateTokenUnitSystem}=require(path.join(engine,'build/server/game/gameSystems/CreateTokenUnitSystem')));
({CardPhaseLastingEffectSystem}=require(path.join(engine,'build/server/game/gameSystems/CardPhaseLastingEffectSystem')));
}
const buyTimeProfile={"title": "Buy Time", "subtitle": "", "cost": 3, "hp": null, "power": null, "text": "Create a Mandalorian token and give it Sentinel for this phase. (Enemy units in its arena must attack a Sentinel when they attack you.)", "deployBox": null, "epicAction": "", "unique": false, "rules": null, "upgradePower": null, "upgradeHp": null, "id": "6201936455", "aspects": ["vigilance"], "traits": ["tactic"], "keywords": ["sentinel"], "types": ["event"], "setId": {"set": "ASH", "number": 91}, "setCodes": [{"set": "ASH", "number": 91}], "internalName": "buy-time"};
const mandalorianProfile={"title": "Mandalorian", "subtitle": "", "cost": 0, "hp": 2, "power": 2, "text": "Shielded (When you create this token, give a Shield token to it.)", "deployBox": null, "epicAction": "", "unique": false, "rules": null, "upgradePower": null, "upgradeHp": null, "id": "8192010342", "aspects": ["vigilance"], "traits": ["mandalorian"], "arena": "ground", "keywords": ["shielded"], "types": ["token", "unit"], "setId": {"set": "ASH"}, "internalName": "mandalorian"};
const helgaitProfile={"title": "Helgait", "subtitle": "Dooku Was a Visionary", "cost": 5, "hp": 4, "power": 6, "text": "When Defeated: You may distribute a number of Advantage tokens equal to this unit's power among friendly units (divided as you choose).", "deployBox": null, "epicAction": "", "unique": true, "rules": "Abilities that refer to a card\u2019s power include temporary modifiers.\n", "upgradePower": null, "upgradeHp": null, "id": "9419144933", "aspects": ["cunning", "villainy"], "traits": ["separatist"], "arena": "ground", "keywords": [], "types": ["unit"], "setId": {"set": "ASH", "number": 195}, "setCodes": [{"set": "ASH", "number": 195}], "internalName": "helgait#dooku-was-a-visionary"};
const advantageProfile={"title": "Advantage", "subtitle": "", "cost": 0, "hp": 0, "power": 1, "text": "When attached unit's attack or defense ends: Defeat this upgrade.", "deployBox": null, "epicAction": "", "unique": false, "rules": "When Attack Ends/When Defense Ends abilities trigger at the same time as units deal combat damage.\n", "upgradePower": 1, "upgradeHp": 0, "id": "5844562972", "aspects": [], "traits": ["innate"], "keywords": [], "types": ["token", "upgrade"], "setId": {"set": "ASH"}, "internalName": "advantage"};
const razorProfile={"title":"Razor Crest","subtitle":"Outfitted Armament","cost":4,"hp":5,"power":3,"text":"Saboteur (When this unit attacks, ignore Sentinel and defeat the defender's Shields.)\nOn Attack: You may discard a card from your hand. If you do, this unit gets +2/+0 for this attack.","deployBox":null,"epicAction":"","unique":true,"rules":null,"upgradePower":null,"upgradeHp":null,"id":"4046328280","aspects":["aggression"],"traits":["mandalorian","vehicle","transport"],"arena":"space","keywords":["saboteur"],"types":["unit"],"setId":{"set":"ASH","number":172},"setCodes":[{"set":"ASH","number":172}],"internalName":"razor-crest#outfitted-armament"};
const surprisesProfile={"title":"Full of Surprises","subtitle":"","cost":2,"hp":null,"power":null,"text":"Return an upgrade that costs 2 or less to its owner's hand.\nGive a Shield token to a unit.","deployBox":null,"epicAction":"","unique":false,"rules":"Abilities that return a card to hand must choose a card in play unless otherwise specified.\nAbilities that refer to a card\u2019s cost always refer to its printed cost, regardless of modifiers.\n","upgradePower":null,"upgradeHp":null,"id":"4547747622","aspects":["cunning"],"traits":["trick"],"keywords":[],"types":["event"],"setId":{"set":"ASH","number":232},"setCodes":[{"set":"ASH","number":232}],"internalName":"full-of-surprises"};
const shieldProfile={"title":"Shield","subtitle":null,"cost":0,"hp":0,"power":0,"text":"If damage would be dealt to attached unit, prevent that damage. If you do, defeat a Shield token on it.","deployBox":null,"epicAction":null,"unique":false,"rules":null,"upgradePower":0,"upgradeHp":0,"id":"8752877738","aspects":[],"traits":["armor"],"keywords":[],"types":["token","upgrade"],"setId":{"set":"SOR"},"internalName":"shield"};
const experienceProfile={"title":"Experience","subtitle":null,"cost":0,"hp":1,"power":1,"text":null,"deployBox":null,"epicAction":null,"unique":false,"rules":null,"upgradePower":1,"upgradeHp":1,"id":"2007868442","aspects":[],"traits":["learned"],"keywords":[],"types":["token","upgrade"],"setId":{"set":"SOR"},"internalName":"experience"};
const weaknessProfile={"title":"Weakness","subtitle":"","cost":0,"hp":-1,"power":-1,"text":"","deployBox":null,"epicAction":"","unique":false,"rules":null,"upgradePower":-1,"upgradeHp":-1,"id":"7816991190","aspects":[],"traits":["condition"],"keywords":[],"types":["token","upgrade"],"setId":{"set":"HMW"},"internalName":"weakness"};
const inputHashes={"server/game/cards/08_ASH/units/RazorCrestOutfittedArmament.ts":"ad7057b85f368cca178e6344e8b0d243e932a41589e19dcd8bbae9dcd3da9a57","build/server/game/cards/08_ASH/units/RazorCrestOutfittedArmament.js":"bbd57f68a7f5376d404e46b87468b42b00f7f841258a32f587021aa4f3fcdf08","server/game/cards/08_ASH/events/FullOfSurprises.ts":"3cb0333b17b8ceecc49539d3fe48bfda6c3ea32a05ff4595f5095fcddd7af280","build/server/game/cards/08_ASH/events/FullOfSurprises.js":"81da110a003d0eaf13d8b7e40ed909bcf600e77d2313691a8dd566221f07de08","server/game/cards/01_SOR/tokens/Shield.ts":"39f1c6699c36ba309a8fe8e053f9b94ddbb8877991767b6664fcd88d447be91f","build/server/game/cards/01_SOR/tokens/Shield.js":"7390ebebb568cb308b28126557c50c6ddf996049815d6ee2dd319d0b27cda5aa","server/game/cards/01_SOR/tokens/Experience.ts":"fccf00d13061bfc15447101a0dc82fc360f9b5d2e28a9da678684e8c93bc9d67","build/server/game/cards/01_SOR/tokens/Experience.js":"8bba7b98315d5ae7d2f60471faafa81fe4cfa01819e4ea6fd5d6d68c06ada305","server/game/cards/09_HMW/tokens/Weakness.ts":"dd546e4886757d77fffeb8be6e7381144fa7378b6493ce444aa87e4ba1202778","build/server/game/cards/09_HMW/tokens/Weakness.js":"aeadb902e97f36b6bc515c8633f22b1530381341cc38e8503040acd5e25d4298","server/game/abilities/keyword/SaboteurDefeatShieldsAbility.ts":"cd131ade6595b0572075e942546641f64c64cee8833656ed274c7864a8a09cf7","build/server/game/abilities/keyword/SaboteurDefeatShieldsAbility.js":"0f5653aca2dce349fd9012137a756ce92d5b532912f6e9af33581ee63d4c8dbd","server/game/gameSystems/MoveCardSystem.ts":"fffa3f43ec7e0461a76762d973fc57ec0835831629cfeef2fd1299959dbfa973","build/server/game/gameSystems/MoveCardSystem.js":"0d0d69bafc7ff062528907ce089334f5cae90c316c0c28fa493cab43e7284542","server/game/gameSystems/SelectCardSystem.ts":"21359f9d0fbefbbc24051df817f1c40b2757e736a67d52513cc075ac86882219","build/server/game/gameSystems/SelectCardSystem.js":"83d0ea95ff91df5cc90517f447e09d1c2aabe27138580fb0ba574fb180daf112","server/game/gameSystems/SimultaneousSystem.ts":"ddc2f93ac1cc09fd3da9658982d86b0021c8bf06aa80e156446af6b8bd17424f","build/server/game/gameSystems/SimultaneousSystem.js":"06566945131647eb95f2e9ba99b7e6873777b4d26ffd5f3bd43f251bb40e417b","server/game/gameSystems/SimultaneousOrSequentialSystem.ts":"da172bd6d07c6f54c68e48bd26cd54028efa7ee4bbe9790b08d5b136c616b6dc","build/server/game/gameSystems/SimultaneousOrSequentialSystem.js":"d17267ade28fbd156b02d6179a48b4d1d0503f7c2f5741ba52b12213d0758df9","server/game/gameSystems/DefeatCardSystem.ts":"3e7d5c860539aba5ffd0b9272601000faf53180d01b6f9e520451cd7e7539b87","build/server/game/gameSystems/DefeatCardSystem.js":"e62165e6f6bcee59f0d3d778d928692813bce3990b0fc13c96ea077c1ab17611","server/game/gameSystems/FrameworkDefeatCardSystem.ts":"c8974173c60fb52ebcfa259543f5b6e99784c4c7c38892a45c38e2daaab035a4","build/server/game/gameSystems/FrameworkDefeatCardSystem.js":"696bcfc492e7ef24ef3c6c7df9caea565ce21ad97fa1d6b73b24f81d72b8ba51","server/game/gameSystems/DiscardCardsFromHandSystem.ts":"60b701f1a9f59c59683fcc3973636b6147b58ad6cf62f87191afe3e8708c3d03","build/server/game/gameSystems/DiscardCardsFromHandSystem.js":"c3fe4353b5c84c7224458de45a7e304b18d953a9d2eb0c2352751342243652f5","server/game/gameSystems/DiscardSpecificCardSystem.ts":"20a42ed816129dd6bc614257df203fbb2d8252e72ebacef917905731e882a774","build/server/game/gameSystems/DiscardSpecificCardSystem.js":"bf336b8f868135a25129dd3876811fef89a559edc66afd6fd9ff7d6633a9b436","server/game/gameSystems/CardAttackLastingEffectSystem.ts":"3b99856085eac6415bd7014f214ffe2df3b70afb7c436ccebbcbe30fa9cde932","build/server/game/gameSystems/CardAttackLastingEffectSystem.js":"db8a9355c8c79685495b6313a6a1112f3ef996a861892f877a286ba8c3fa2c71","server/game/gameSystems/AttackStepsSystem.ts":"f6209f9b7ec9e8e3fbf30e193294a1df466d02e81988d544edd0a74d26988b38","build/server/game/gameSystems/AttackStepsSystem.js":"212b0773b91e73eb2d9ece43c7dfa9dc615f76dcfcd06df4df14297bcc8cd8f8","test/json/Card/razor-crest#outfitted-armament.json":"d053b751e41e2f4c10f9d3d28f734d66d229ff670cd1cccf4cb60ae5c216fb4e","test/json/Card/full-of-surprises.json":"da677e84423dc75fa9ea7ae5c6ed157a1c448caa60632390ef277fa82016b101","test/json/Card/shield.json":"3fe37b5b4c214e1a6971c2ea5e7729a7cad9bf983a384c20b56c404cbf41208b","test/json/Card/experience.json":"cc1d7a3bf3344d8a95afdbba8607659ec1edd07e5282bb9eb9d3497b0f7f332b","test/json/Card/weakness.json":"6a8e3afbc95ff1ddbceb2edf8aafdfd558a8ce5b148c375e45f250792ae96fd7",
  "server/game/cards/08_ASH/events/BuyTime.ts": "6658f3027c842eac57033101b423e236e43e10654adc2f7dab4703675a6d2c32",
  "server/game/core/ability/CardAbilityStep.ts": "523dd116f740ef9a67b2667731644a6279727daf7ba37c493ca41786083d4b3e",
  "server/game/core/event/EventWindow.ts": "ee180d966d995d9ffc52df8f22a8c669f2b4e113ef69815a107127aec5fae674",
  "server/game/gameSystems/CreateTokenUnitSystem.ts": "178e8bbbf971ec80cdc608cb2b4559ecb3ca5e2fcfdecab288adc6e56ea70fbd",
  "server/game/gameSystems/CardLastingEffectSystem.ts": "d47af53160ce8d7a83413097e8e923d0aed4528110ce2d14410c2beca98a5167",
  "server/game/gameSystems/CardPhaseLastingEffectSystem.ts": "11093bf36c75a916ee9bfc3d62dd96f4e9a2704613326f816662493ba022fff1",
  "server/game/core/ongoingEffect/OngoingEffect.ts": "dbe2714c8f8180687fb8ba19ec5049ea6e077733f01c3dd86e559d3fc10bae34",
  "server/game/core/ongoingEffect/effectImpl/GainKeyword.ts": "116434579850ee9e31281a9b88873c6fee43d457b0ef7d45ac351da20eb21826",
  "server/game/core/ongoingEffect/effectImpl/StaticOngoingEffectImpl.ts": "07a3c6bbd574f9408c3ba72d7cf95107f8f5a78d88d9e1aba0f63f15c9dce8b4",
  "build/server/game/cards/08_ASH/events/BuyTime.js": "02eb6bfe47a367dcc5d50315235ce0f5d5607469687addddf5c81ca41002b13d",
  "build/server/game/core/ability/CardAbilityStep.js": "e4e4c6ebe7318f1f6d9fc8fde6fc8bae55456fa427554d147961be6834f566f3",
  "build/server/game/core/event/EventWindow.js": "ab6ee6e8a671531b626725a2bb0c9dfac6ed854ddb1667d0e2d915f3220662e5",
  "build/server/game/gameSystems/CreateTokenUnitSystem.js": "8744fe00df80e1a82cd0ec6173196ed1942255bcc7b9a83f0f97ba26399a26dc",
  "build/server/game/gameSystems/CardLastingEffectSystem.js": "1b1b978128743f23e6dbec4ec39652b48d84165504f5f84983df6bc4015dea61",
  "build/server/game/gameSystems/CardPhaseLastingEffectSystem.js": "79c805adfde8066818ea8c9dbb59a1bd86bee0d5b3364faa7677aed16650855a",
  "build/server/game/core/ongoingEffect/OngoingEffect.js": "57db9e704629294fb6d7aea452e37718097874505a8b19f94f38b8b6a343245b",
  "build/server/game/core/ongoingEffect/effectImpl/GainKeyword.js": "503a2972c2771613e8ea91b0b6c1c7bee8543390267376a4f97f0310315cf693",
  "build/server/game/core/ongoingEffect/effectImpl/StaticOngoingEffectImpl.js": "be70e3e0ae2ccb2e9d648549290373ec54eb89a63a34997a2b2ae22a19a9665c",
  "server/game/AbilityHelper.ts": "6ef4ef44e1f9a1fbf9e834fac10b2a34a260eb1cd31b80c6fa7400d1e8aa9f0f",
  "server/game/ongoingEffects/OngoingEffectLibrary.ts": "80ec23b1e4910814de9dba4264dc1f49945bc74524bc27fbb0b6b59c0f76fe30",
  "server/game/gameSystems/GameSystemLibrary.ts": "2cba31deb4ad198180d1a21b3a8a52585aea3399520dfb61ccb48bcb73f9525b",
  "server/game/core/gameSystem/PlayerTargetSystem.ts": "ac3b63da8d7c697f39c3472d6f10f253ecbafa851ec56acba8a878d706dbd313",
  "server/game/core/gameSystem/GameSystem.ts": "25d6049630d2544f084b67a994953069254781f0356450d91c7ec0049173101f",
  "server/game/core/gameSystem/CardTargetSystem.ts": "e87cfa4984927681af8dfb06bfa2a242f00ec867bf28271db9442c436f245d63",
  "server/game/core/ability/EventAbility.ts": "cdcbf49379801e5e855a50836fc1cbd076119a66ea560057f7c341752f49ae1a",
  "server/game/core/Game.ts": "bfb2fa16f3381b1c3f32ea8240b32392e40217a533cac3e603f7645bf214071c",
  "build/server/game/AbilityHelper.js": "4e2fb2f431d7cfa3f2fc0687717542f8a86adff74926b35d5342d81f14582bbf",
  "build/server/game/ongoingEffects/OngoingEffectLibrary.js": "754051faf87183206c167eca296184251fb1bb48ed85e5cac8a3618d95490cc3",
  "build/server/game/gameSystems/GameSystemLibrary.js": "df01068a41895dd67e8c8418fceee95070b37410af395c25f9869dee26d9c3fe",
  "build/server/game/core/gameSystem/PlayerTargetSystem.js": "184f3e26ec407a4b2e1972e68bcb036294ed28562cecfba660b938a8cd4e1921",
  "build/server/game/core/gameSystem/GameSystem.js": "7b4877c986b846f069c44b2e5e924b33728b93eb449bdad13dbc81640dcda831",
  "build/server/game/core/gameSystem/CardTargetSystem.js": "ae0e2f4804e955a4b45ba5468ae58eb4db441031a243aa49e4d1b85a5ca1be82",
  "build/server/game/core/ability/EventAbility.js": "19ce5808bf2268ac8be8c57e7095b02429529504e4350732946b0d7431c3c169",
  "build/server/game/core/Game.js": "b8d587cdd9d557101714d79f1bed95cd5c07918205b2411ed5b494d860ff396b",
  "server/game/core/snapshot/SnapshotManager.ts": "93e0e9cb68ad4baae58f5b8247e1decd5a523b8b6e8a025e91dc14ea3eb5efe2",
  "build/server/game/core/snapshot/SnapshotManager.js": "867f6621b0b17fc1cd6ab43828783bbc58a6a6f8c5347dfcc23b4427257166ed",
  "server/game/cards/08_ASH/units/HelgaitDookuWasAVisionary.ts": "19281e10cd7a6648ed5b8162cce726777a3dc1cc4f6bd5e9f776832bee06e39f",
  "server/game/cards/08_ASH/tokens/Advantage.ts": "1280861b9a94572ecce2c1d62fb5fd93c11b08609495c3d9f60e656d153e3119",
  "server/game/core/card/baseClasses/InPlayCard.ts": "78f7325e62b289868f8a64b7645ae0ac30408e622921b4a0c8ec0935130e16e1",
  "server/game/core/card/propertyMixins/TriggeredAbilityRegistration.ts": "0feb23d92b2d67c1c2f31368c5fe1c99f4a23d4a7d506db419b70a0da2d783f3",
  "server/game/core/ability/TriggeredAbility.ts": "f9c08ce8158b482356554128bdc2f7112ff289c599bdb30235a412483304bdfd",
  "server/game/gameSystems/DistributeAmongTargetsSystem.ts": "7eff9809c0628280f63f42e68cce357919b38498f36525caa0840f327f78c787",
  "server/game/gameSystems/DistributeTokenUpgradeSystem.ts": "4f92e71450125e5cf6d9a341819297431d05a35b388a11b9b8ea10d605e76238",
  "server/game/gameSystems/GiveTokenUpgradeSystem.ts": "b8048ebcc0daf229a546b5b4e3a72919cc501cf0dd0883ad5afad3d0d24968b8",
  "server/game/core/card/TokenCards.ts": "b82d4654f1c01e3d780c0f93df38cef20a457a7164c282819389de576d600297",
  "server/game/core/card/propertyMixins/Token.ts": "3f503f6ec00df17b9b048c288b527495ae26be2710ccf67bbc95ba471d2776a7",
  "server/game/core/card/UpgradeCard.ts": "79e74d72c0187be164ea8a8d6bdf8f0904a89cd4378170ffdaf673e55a99e738",
  "build/server/game/cards/08_ASH/units/HelgaitDookuWasAVisionary.js": "0db9a38211078366839a0a72f95e28e377fd0ffef56568d5dc473f2c93511bb7",
  "build/server/game/cards/08_ASH/tokens/Advantage.js": "68cb736da5bfa06b1ed23cd5b508de62202efe008b28e21ccbd6ae3839694646",
  "build/server/game/core/card/baseClasses/InPlayCard.js": "14c59a69d8b8137af47b86ed343148df574ca1be5d6d722205ea3f9c28fd19e2",
  "build/server/game/core/card/propertyMixins/TriggeredAbilityRegistration.js": "9a40179fc1bd13bfcd4898e7ef69cc196b9f948b41af309efcad271178aacd39",
  "build/server/game/core/ability/TriggeredAbility.js": "603bb8dae9cdc10867f520d4f1f0a5a0badf1f2c8d6dce41d887432030052a56",
  "build/server/game/gameSystems/DistributeAmongTargetsSystem.js": "696e321f3e27ebcf8de87a55f9b399a83bf6f452af28b9fda3b834e68f039833",
  "build/server/game/gameSystems/DistributeTokenUpgradeSystem.js": "672fa3844e8731634ac037f8ca575f1d102c66a670beaf528a1378b9d5816f90",
  "build/server/game/gameSystems/GiveTokenUpgradeSystem.js": "35a71e2e367cc3c86d7e809cbd5daabdeb4b7b9c146195fa13c4a5a774bd483b",
  "build/server/game/core/card/TokenCards.js": "908943694d231516025c23dad1b39b54fe8335d50dee91b0bb206303e1bc6f26",
  "build/server/game/core/card/propertyMixins/Token.js": "9579e1e603b33d92ab1650fa3c98254dbab1d18ba450aa7bde55369955047d71",
  "build/server/game/core/card/UpgradeCard.js": "03a5b6eceaa9f11c05b8032c754cfaaa4eeaab7468f325652e28c82309e74a65",
  "test/json/Card/helgait#dooku-was-a-visionary.json": "f5988763a096e10465c99788c44907c71790d10b078116ebb67d8fbbf6dfa13d",
  "test/json/Card/advantage.json": "9a81c2d083caa13d2a5a173bdeedf76e837d62fb413496e8539338b42d71ce94",
  "server/game/cards/Index.ts": "1b411c5b5a4d55ad9084ee5d8cbf1e46d4ed02dfba8ebaa971dec7667370ef2f",
  "build/server/game/cards/Index.js": "854a5f0defb0585e6eb0594c2b0ddc7c93d5e1e70b821e3f52ce86aa170d56f8",
  "server/game/core/GameObjectUtils.ts": "092ab95caaf4322f3eec02c239d04efdffaa33dc82c406e92bed04d10fb37c3f",
  "build/server/game/core/GameObjectUtils.js": "35fb6a35e405891f3cda16be0f6ed894ad32e9490273a56023522f8426f2d66a"
};
const thenFunctionHash="db56825c8de5a97cdad27ee4401b8625ef1ea2f2fd028a62053d565965969ec1";
const observations = new WeakMap(), companions = new WeakMap();
const fail = message => { throw Error('Unsupported inactive phase keyword state: ' + message); };
const check = (condition, message) => { if (!condition) fail(message); };
const keys = (o, expected) => o && isDeepStrictEqual(Object.keys(o).sort(), expected.slice().sort());
const arena = c => ['groundArena', 'spaceArena'].includes(c.zoneName);
function pinned() {
    for (const [file, hash] of Object.entries(inputHashes)) check(sha(fs.readFileSync(path.join(engine, file))) === hash, 'changed pinned input ' + file);
}
// Routing is deliberately broader than authorization. Any physical lookalike
// must reach the strict projection, including partial metadata and set aliases.
function physicalSourceHint(card, profile, raw) {
    const code=profile.setId.set+'_'+String(profile.setId.number).padStart(3,'0');
    const aliases=[card?.cardData?.setId,...(Array.isArray(card?.cardData?.setCodes)?card.cardData.setCodes:[])];
    return card instanceof raw || card?.cardData?.id===profile.id || card?.internalName===profile.internalName || card?.cardData?.internalName===profile.internalName || card?.setCode===code || card?.cardData?.setCode===code || aliases.some(set=>set?.set===profile.setId.set && set?.number===profile.setId.number);
}
function hasInactiveInventorySource(eg) {
    loadEngineTypes();
    return (eg.game?.state?.allCards??[]).some(uuid=>{
        const card=eg.game.getFromId(uuid);
        return [[buyTimeProfile,BuyTime],[helgaitProfile,Helgait],[razorProfile,RazorCrest],[surprisesProfile,FullOfSurprises]].some(([profile,raw])=>physicalSourceHint(card,profile,raw));
    });
}
function sourceProof(source, ability) {
    check(source instanceof BuyTime && isDeepStrictEqual(source.cardData, buyTimeProfile), 'complete Buy Time physical profile');
    check(ability === source.getEventAbility() && ability.printedAbility === true && ability.card === source && ability.gainAbilitySource == null, 'printed parent identity');
    check(keys(ability.properties, ['title', 'immediateEffect', 'then', 'cardName', 'triggerHandlingMode']) && ability.properties.immediateEffect === ability.immediateEffect && ability.properties.cardName === 'Buy Time', 'parent registration envelope');
    check(ability.immediateEffect instanceof CreateTokenUnitSystem && ability.immediateEffect.name === 'createTokenUnit' && ability.targetResolvers.length === 0 && ability.cost.length === 0 && ability.optional === false, 'parent system');
    check(sha(Function.prototype.toString.call(ability.properties.then)) === thenFunctionHash, 'pinned parent continuation function');
}
/** Must be installed before initialization. Observes the existing event emitter only;
 * does not create cards/effects, wrap engine methods, mutate engine state, or allocate IDs.
 * Undo is intentionally unsupported: a receipt proves this one forward execution.
 */
function observeInactivePhaseKeywords(eg) {
    check(!eg.started && !observations.has(eg), 'observer must be installed once before initialization');
    check(eg.game?.isUndoEnabled === false, 'undo-enabled games require chronological state proof');
    pinned(); loadEngineTypes();
    const state = { creations: new Map(), before: new WeakMap(), effects: new Map(), initialIds: null };
    observations.set(eg, state);
    eg.game.on('onTokensCreated', event => {
        if (!(event.context?.source instanceof BuyTime)) return;
        sourceProof(event.context.source, event.context.ability);
        check(event.context.game === eg.game && event.context.source.game === eg.game, 'parent game identity');
        check(event.tokenType === 'mandalorian' && event.generatedTokens?.length === 1 && event.player === event.context.player, 'exact successful creation result');
        const target = event.generatedTokens[0];
        check(isDeepStrictEqual(target.cardData, mandalorianProfile) && target.owner === event.context.player && target.controller === event.context.player, 'generated token physical profile/ownership');
        check(!state.creations.has(target), 'duplicate creation receipt');
        state.creations.set(target, { event, source: event.context.source, parent: event.context.ability });
    });
    eg.game.on('onEffectApplied:preResolve', event => {
        if (!(event.context?.source instanceof BuyTime)) return;
        const creation = state.creations.get(event.card), ability = event.context.ability;
        check(creation?.source === event.context.source && !creation.consumed && event.context.game === eg.game && event.context.player === creation.event.context.player, 'unobserved or foreign generated target');
        sourceProof(creation.source, creation.parent);
        check(ability.properties.title === 'Give it Sentinel for this phase' && ability.properties.triggerHandlingMode === creation.parent.properties.triggerHandlingMode, 'closed continuation registration');
        check(ability instanceof FrameworkCardAbilityStep && ability.card === creation.source && ability.printedAbility == null && ability.gainAbilitySource == null, 'nongained continuation identity');
        check(keys(ability.properties, ['title', 'immediateEffect', 'triggerHandlingMode']) && ability.immediateEffect instanceof CardPhaseLastingEffectSystem && ability.properties.immediateEffect === ability.immediateEffect, 'continuation envelope');
        const p = ability.immediateEffect.properties;
        check(keys(p, ['effect', 'target', 'duration']) && p.duration === 'untilEndOfPhase' && Array.isArray(p.target) && p.target.length === 1 && p.target[0] === event.card, 'captured physical continuation target');
        check(ability.targetResolvers.length === 0 && ability.cost.length === 0 && ability.optional === false, 'continuation system');
        state.before.set(event, { creation, ability, effects: eg.game.ongoingEffectEngine.effects.slice() });
    });
    eg.game.on('onEffectApplied', event => {
        if (!(event.context?.source instanceof BuyTime)) return;
        const before = state.before.get(event);
        check(before && before.ability === event.context.ability, 'missing pre-resolution receipt');
        const registry = eg.game.ongoingEffectEngine.effects;
        check(before.effects.every(e => registry.includes(e)), 'foreign registry mutation during application');
        const added = registry.filter(e => !before.effects.includes(e));
        check(added.length === 1, 'exact one resulting effect');
        const effect = added[0]; validateEffect(effect, event.card, before.creation.source, before.ability, true);
        before.creation.consumed = true;
        state.effects.set(effect, { target: event.card, source: before.creation.source, ability: before.ability, creation: before.creation });
    });
    return undefined;
}
function validateEffect(effect, target, source, ability, preRefresh = false) {
    check(effect.type === 'gainKeyword' && effect.duration === 'untilEndOfPhase' && effect.source === source && effect.matchTarget === target && effect.sourceZoneFilter === 'any', 'lasting effect identity');
    check(keys(effect.ongoingEffect, ['matchTarget', 'sourceZoneFilter', 'isLastingEffect', 'ability', 'target', 'duration']), 'lasting property envelope');
    const p = effect.ongoingEffect;
    check(p.matchTarget === target && p.ability === ability && p.isLastingEffect === true && p.sourceZoneFilter === 'any' && p.duration === 'untilEndOfPhase' && Array.isArray(p.target) && p.target.length === 1 && p.target[0] === target, 'lasting captured binding');
    check((preRefresh ? effect.targets.length === 0 : effect.targets.length === 1 && effect.targets[0] === target) && effect.impl.isConditional === false && effect.targetsSourceOnly === false && effect.targetController === 'self' && effect.targetZoneFilter === 'any' && isDeepStrictEqual(effect.targetCardTypeFilter, ['unit']), 'lasting scope');
    check(isDeepStrictEqual(effect.getValue(target), { keyword: 'sentinel' }), 'exact Sentinel value');
}
function idNumber(id) { check(/^c(?:0|[1-9][0-9]*)$/.test(id), 'canonical physical id'); return Number(id.slice(1)); }
function liveRefs(eg, players) {
    const ids = new Map(), all = eg.game.state.allCards;
    const visit = (value, at) => {
        if (!value || typeof value !== 'object') return;
        if (Object.hasOwn(value, 'id')) {
            const index = idNumber(value.id); check(index < all.length, 'live reference exceeds allocation');
            const card = eg.game.getFromId(all[index]); check(card, 'live physical object missing');
            if (value.name != null) check(value.name === card.internalName, 'contradictory live name');
            if (value.setCode != null) check(value.setCode === descriptor(eg, card, index).setCode, 'contradictory live definition');
            if (value.name == null && value.setCode == null) check(card.isForceToken?.() || card.isCreditToken?.(), 'unproven virtual live reference');
            if (ids.has(value.id)) {
                // The ordinary state schema describes a deployed leader in both
                // its leader slot and arena. This is one existing physical ID.
                const prior = ids.get(value.id);
                check(card.isLeader?.() && arena(card) && prior.length === 1 && ((/\.leader$/.test(prior[0]) && /\.(ground|space)\[\d+\]$/.test(at)) || (/\.leader$/.test(at) && /\.(ground|space)\[\d+\]$/.test(prior[0]))), 'duplicate live identity');
                prior.push(at);
            } else ids.set(value.id, [at]);
        }
        for (const [key, child] of Object.entries(value)) if (key !== 'id') {
            if (Array.isArray(child)) child.forEach((x, i) => visit(x, at + '.' + key + '[' + i + ']'));
            else if (child && typeof child === 'object') visit(child, at + '.' + key);
        }
    };
    check(keys(players, ['p1', 'p2']), 'both player projections'); visit(players, 'players'); return new Set(ids.keys());
}
function descriptor(eg, card, index) {
    const owner = eg.seatOf(card.owner?.id), controller = eg.seatOf(card.controller?.id);
    check(['p1', 'p2'].includes(owner) && ['p1', 'p2'].includes(controller), 'physical ownership');
    const set = card.cardData.setId;
    let code = set?.number != null ? set.set + '_' + String(set.number).padStart(3, '0') : null;
    if (card.isToken?.()) code = 'TOKEN_' + card.internalName.replace(/[^a-z0-9]+/gi, '_').toUpperCase();
    check(typeof code === 'string' && code.length > 0 && typeof card.internalName === 'string', 'physical definition');
    return { id: 'c' + index, name: card.internalName, setCode: code, owner, controller };
}
/** Existing live player refs are supplied verbatim by fullState's producer. The
 * complement includes EVERY already allocated omitted identity, even after expiry.
 * Source/origin is internal proof only, never serialized as unsupported history.
 */
function inactivePhaseKeywordProjection(eg, players) {
    const state = observations.get(eg); check(state, 'preplay observation missing');
    check(eg.game?.isUndoEnabled === false, 'undo-enabled games require chronological state proof');
    check(eg.ids.some(pid => eg.isActionWindow(pid)) || (eg.over && !eg.game.currentAbilityResolver && !eg.game.currentAttack), 'projection outside stable window');
    const all = eg.game.state.allCards, objects = all.map(uuid => eg.game.getFromId(uuid));
    check(new Set(all).size === all.length && objects.every((c, i) => c && c.uuid === all[i]) && new Set(objects).size === all.length, 'complete allocated identity registry');
    if (state.initialIds) check(all.length >= state.initialIds.length && state.initialIds.every((uuid, i) => all[i] === uuid), 'allocation rollback or identity drift');
    state.initialIds = all.slice();
    const newProfiles=[{profile:razorProfile,raw:RazorCrest,registered:RegisteredRazor,unit:true},{profile:surprisesProfile,raw:FullOfSurprises,registered:RegisteredSurprises,unit:false}];
    const newMatch=c=>newProfiles.find(p=>physicalSourceHint(c,p.profile,p.raw));
    const reviewedTokens=[{profile:shieldProfile,registered:RegisteredShield},{profile:experienceProfile,registered:RegisteredExperience},{profile:advantageProfile,registered:RegisteredAdvantage},{profile:weaknessProfile,registered:RegisteredWeakness}];
    const sources = objects.filter(c => newMatch(c) || physicalSourceHint(c,buyTimeProfile,BuyTime) || physicalSourceHint(c,helgaitProfile,Helgait));
    for (const source of sources) {
        check(source.owner === source.controller, 'unsupported allocated inventory source control transfer');
        const candidate=newMatch(source);
        if(candidate){
            const {profile,raw,registered,unit}=candidate;
            check(Object.getPrototypeOf(source)===registered.prototype && isDeepStrictEqual(source.cardData,profile) && !source.isToken?.() && !source.isLeader?.() && (unit ? source.isUnit?.() && !source.isUpgrade?.() : source.isEvent?.() && !source.isUnit?.() && !source.isUpgrade?.()), 'complete allocated closed172/232 profile');
            check(source.setupCardAbilities===raw.prototype.setupCardAbilities && source.getImplementationId===raw.prototype.getImplementationId,'closed172/232 registration methods');
            for(const {profile:token}of reviewedTokens)check(isDeepStrictEqual(eg.game.cardDataGetter.getCardSync(token.id),token),'reviewed raw token upgrade definition');
        } else if (physicalSourceHint(source,buyTimeProfile,BuyTime)) {
            check(source instanceof BuyTime && isDeepStrictEqual(source.cardData, buyTimeProfile), 'complete allocated source profile');
        } else {
            check(Object.getPrototypeOf(source) === RegisteredHelgait.prototype && isDeepStrictEqual(source.cardData, helgaitProfile) && source.isUnit?.() && !source.isToken?.() && !source.isLeader?.(), 'complete allocated Helgait profile');
            // Inventory eligibility comes from the closed printed definition, not
            // the current blanked/gained ability list or an effect-origin guess.
            check(source.setupCardAbilities === Helgait.prototype.setupCardAbilities && source.getImplementationId === Helgait.prototype.getImplementationId, 'closed Helgait registration methods');
            check(isDeepStrictEqual(eg.game.cardDataGetter.getCardSync(advantageProfile.id), advantageProfile), 'reviewed raw Advantage definition');
        }
    }
    const hasSource = sources.length > 0;
    const rows = [], registry = eg.game.ongoingEffectEngine.effects;
    if (!hasSource) {
        for (const card of objects.filter(c => !arena(c))) {
            check(!(card.getOngoingEffects?.() ?? []).some(e => ['gainKeyword', 'loseKeyword'].includes(e.type) && e.duration === 'untilEndOfPhase'), 'unproved inactive keyword without source');
            check(!registry.some(e => ['gainKeyword', 'loseKeyword'].includes(e.type) && e.duration === 'untilEndOfPhase' && (e.matchTarget === card || e.targets?.includes(card))), 'unproved inactive registry keyword without source');
        }
        return {};
    }
    const live = liveRefs(eg, players); for (const id of live) check(idNumber(id) < all.length, 'live reference exceeds allocation');
    for (const [index, card] of objects.entries()) {
        if (live.has('c' + index)) {
            if (!(arena(card) && card.isUnit?.())) {
                const unserialized = e => ['gainKeyword', 'loseKeyword'].includes(e.type) && e.duration === 'untilEndOfPhase';
                check(!(card.getOngoingEffects?.() ?? []).some(unserialized) && !registry.some(e => unserialized(e) && (e.matchTarget === card || e.targets?.includes(card))), 'unserialized phase keyword on non-unit-arena live reference');
            }
            continue;
        }
        check((card.zoneName === 'outsideTheGame' || card.zoneName == null) && card.isToken?.() && !card.isForceToken?.(), 'omitted live/unsupported identity');
        if (card instanceof Advantage || card.internalName === advantageProfile.internalName || card.cardData?.id === advantageProfile.id) {
            check(Object.getPrototypeOf(card) === RegisteredAdvantage.prototype && isDeepStrictEqual(card.cardData, advantageProfile) && card.isToken?.() && card.isUpgrade?.() && !card.isAttached?.(), 'complete detached Advantage profile');
            check((card.getOngoingEffects?.() ?? []).length === 0 && !registry.some(e => e.matchTarget === card || e.targets?.includes(card)), 'unrepresented retired Advantage effect state');
        }
        const tokenProfile=reviewedTokens.find(t=>card.cardData?.id===t.profile.id || card.internalName===t.profile.internalName);
        if(tokenProfile){
            check(Object.getPrototypeOf(card)===tokenProfile.registered.prototype && isDeepStrictEqual(card.cardData,tokenProfile.profile) && card.isUpgrade?.() && card.isToken?.() && !card.isAttached?.(),'complete detached reviewed token upgrade profile');
            check((card.getOngoingEffects?.()??[]).length===0 && !registry.some(e=>e.matchTarget===card || e.targets?.includes(card)),'unrepresented retired token upgrade effect state');
        } else check(!card.isUpgrade?.(),'unreviewed retired token upgrade definition');
        const phaseKeywords = {}, relevant = e => ['gainKeyword', 'loseKeyword'].includes(e.type), keywordEffects = [...new Set([...(card.getOngoingEffects?.() ?? []).filter(relevant), ...registry.filter(e => relevant(e) && (e.matchTarget === card || e.targets?.includes(card)))])];
        for (const effect of keywordEffects) {
            const receipt = state.effects.get(effect);
            check(receipt?.source instanceof BuyTime && receipt?.target === card && registry.includes(effect), 'unproved inactive keyword origin');
            sourceProof(receipt.source, receipt.creation.parent); validateEffect(effect, card, receipt.source, receipt.ability);
            check(isDeepStrictEqual(card.cardData, mandalorianProfile), 'inactive token definition'); phaseKeywords.sentinel = 1;
        }
        const physical = descriptor(eg, card, index);
        check(physical.owner === physical.controller, 'unsupported inactive physical control transfer');
        rows.push({ ...physical, phaseKeywords });
    }
    const projection = { inactivePhaseKeywordStateVersion: 1, inactiveAllocatedCards: rows };
    companions.set(projection, { eg, registry: registry.slice(), rows: rows.map((row, i) => ({ row: structuredClone(row), card: objects[idNumber(row.id)] })) });
    return projection;
}
/** For a separately reviewed unit-entry composition extension. No transformed
 * marker-free stats/card object is passed to the old guard. */
function validatesInactivePhaseKeywordCompanion(projection, eg, card, keywords) {
    if (eg?.game?.isUndoEnabled !== false) return false;
    const proof = companions.get(projection);
    if (!proof || proof.eg !== eg || !keys(projection, ['inactivePhaseKeywordStateVersion', 'inactiveAllocatedCards']) || projection.inactivePhaseKeywordStateVersion !== 1 || !isDeepStrictEqual(projection.inactiveAllocatedCards, proof.rows.map(x => x.row))) return false;
    const current = eg.game.ongoingEffectEngine.effects;
    if (current.length !== proof.registry.length || !current.every((e, i) => e === proof.registry[i])) return false;
    const row = proof.rows.find(x => x.card === card)?.row;
    if (!row || Object.keys(keywords ?? {}).length === 0 || !isDeepStrictEqual(row.phaseKeywords, keywords)) return false;
    try {
        const state = observations.get(eg), effects = current.filter(e => e.matchTarget === card && e.type === 'gainKeyword');
        if (!effects.length) return false;
        for (const effect of effects) { const receipt = state.effects.get(effect); if (!receipt || receipt.target !== card) return false; sourceProof(receipt.source, receipt.creation.parent); validateEffect(effect, card, receipt.source, receipt.ability); }
    } catch { return false; }
    return true;
}
module.exports = { hasInactiveInventorySource, observeInactivePhaseKeywords, inactivePhaseKeywordProjection, validatesInactivePhaseKeywordCompanion };
