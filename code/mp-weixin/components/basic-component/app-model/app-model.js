(global["webpackJsonp"]=global["webpackJsonp"]||[]).push([["components/basic-component/app-model/app-model"],{"000e":function(t,n,e){"use strict";var u=e("be68"),i=e.n(u);i.a},"046d":function(t,n,e){"use strict";e.r(n);var u=e("4197"),i=e.n(u);for(var a in u)["default"].indexOf(a)<0&&function(t){e.d(n,t,(function(){return u[t]}))}(a);n["default"]=i.a},4197:function(t,n,e){"use strict";Object.defineProperty(n,"__esModule",{value:!0}),n.default=void 0;var u={name:"app-model",props:{type:{type:String,default:function(){return"1"}},background:{type:String,default:function(){return"white"}},height:{type:Number,default:function(){return 500}},value:{type:Boolean,default:function(){return!1}}},data:function(){return{display:this.value}},methods:{bubble:function(){return!1},close:function(){this.display=!1,this.$emit("input",this.display)}},computed:{setHeight:function(){return!0===this.display?"0":"-".concat(this.height+108,"rpx")}},watch:{value:function(){this.display=this.value}}};n.default=u},"7a11":function(t,n,e){"use strict";var u;e.d(n,"b",(function(){return i})),e.d(n,"c",(function(){return a})),e.d(n,"a",(function(){return u}));var i=function(){var t=this,n=t.$createElement;t._self._c},a=[]},be68:function(t,n,e){},cf2f:function(t,n,e){"use strict";e.r(n);var u=e("7a11"),i=e("046d");for(var a in i)["default"].indexOf(a)<0&&function(t){e.d(n,t,(function(){return i[t]}))}(a);e("000e");var r,o=e("f0c5"),c=Object(o["a"])(i["default"],u["b"],u["c"],!1,null,"e473a898",null,!1,u["a"],r);n["default"]=c.exports}}]);
;(global["webpackJsonp"] = global["webpackJsonp"] || []).push([
    'components/basic-component/app-model/app-model-create-component',
    {
        'components/basic-component/app-model/app-model-create-component':(function(module, exports, __webpack_require__){
            __webpack_require__('543d')['createComponent'](__webpack_require__("cf2f"))
        })
    },
    [['components/basic-component/app-model/app-model-create-component']]
]);
