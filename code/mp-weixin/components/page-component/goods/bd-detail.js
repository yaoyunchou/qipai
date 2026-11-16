(global["webpackJsonp"]=global["webpackJsonp"]||[]).push([["components/page-component/goods/bd-detail"],{1727:function(t,n,e){"use strict";Object.defineProperty(n,"__esModule",{value:!0}),n.default=void 0;var a=function(){Promise.all([e.e("common/vendor"),e.e("components/basic-component/app-rich/parse")]).then(function(){return resolve(e("cb0e"))}.bind(null,e)).catch(e.oe)},c={name:"bd-detail",components:{"app-rich-text":a},props:{detail:{type:String,default:function(){return""}}},created:function(){this.$store.dispatch("gConfig/setImageWidth",48)},data:function(){return{imageProp:{mode:"aspectFit",padding:0,lazyLoad:!1,domain:"",paddinglimit:""}}},computed:{newDetail:function(){var t="";return this.detail&&(t=this.detail),t}}};n.default=c},"1bab":function(t,n,e){"use strict";var a=e("c000"),c=e.n(a);c.a},"3e70":function(t,n,e){"use strict";e.r(n);var a=e("8cbb"),c=e("41ce");for(var i in c)["default"].indexOf(i)<0&&function(t){e.d(n,t,(function(){return c[t]}))}(i);e("1bab");var o,r=e("f0c5"),u=Object(r["a"])(c["default"],a["b"],a["c"],!1,null,"14cf845c",null,!1,a["a"],o);n["default"]=u.exports},"41ce":function(t,n,e){"use strict";e.r(n);var a=e("1727"),c=e.n(a);for(var i in a)["default"].indexOf(i)<0&&function(t){e.d(n,t,(function(){return a[t]}))}(i);n["default"]=c.a},"8cbb":function(t,n,e){"use strict";var a;e.d(n,"b",(function(){return c})),e.d(n,"c",(function(){return i})),e.d(n,"a",(function(){return a}));var c=function(){var t=this,n=t.$createElement;t._self._c},i=[]},c000:function(t,n,e){}}]);
;(global["webpackJsonp"] = global["webpackJsonp"] || []).push([
    'components/page-component/goods/bd-detail-create-component',
    {
        'components/page-component/goods/bd-detail-create-component':(function(module, exports, __webpack_require__){
            __webpack_require__('543d')['createComponent'](__webpack_require__("3e70"))
        })
    },
    [['components/page-component/goods/bd-detail-create-component']]
]);
