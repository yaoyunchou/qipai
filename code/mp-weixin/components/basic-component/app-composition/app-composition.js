(global["webpackJsonp"]=global["webpackJsonp"]||[]).push([["components/basic-component/app-composition/app-composition"],{"0efbf":function(t,e,n){"use strict";var i=n("3bfe"),c=n.n(i);c.a},"3bfe":function(t,e,n){},"49af":function(t,e,n){"use strict";n.r(e);var i=n("fbcb"),c=n.n(i);for(var o in i)["default"].indexOf(o)<0&&function(t){n.d(e,t,(function(){return i[t]}))}(o);e["default"]=c.a},"7e9e":function(t,e,n){"use strict";var i;n.d(e,"b",(function(){return c})),n.d(e,"c",(function(){return o})),n.d(e,"a",(function(){return i}));var c=function(){var t=this,e=t.$createElement;t._self._c},o=[]},9495:function(t,e,n){"use strict";n.r(e);var i=n("7e9e"),c=n("49af");for(var o in c)["default"].indexOf(o)<0&&function(t){n.d(e,t,(function(){return c[t]}))}(o);n("0efbf");var a,r=n("f0c5"),f=Object(r["a"])(c["default"],i["b"],i["c"],!1,null,"2ac56bde",null,!1,i["a"],a);e["default"]=f.exports},fbcb:function(t,e,n){"use strict";Object.defineProperty(e,"__esModule",{value:!0}),e.default=void 0;n("2f62");var i={name:"app-composition",props:{item:{type:Object},large:Boolean,theme:Object},data:function(){return{price:{priceFloat:"",priceInt:""}}},created:function(){var t=this;t.price=t.handlePrice(t.item.min_composition_price)},methods:{open:function(t){this.$emit("click",t)},toDetail:function(t){this.$emit("look",t)}}};e.default=i}}]);
;(global["webpackJsonp"] = global["webpackJsonp"] || []).push([
    'components/basic-component/app-composition/app-composition-create-component',
    {
        'components/basic-component/app-composition/app-composition-create-component':(function(module, exports, __webpack_require__){
            __webpack_require__('543d')['createComponent'](__webpack_require__("9495"))
        })
    },
    [['components/basic-component/app-composition/app-composition-create-component']]
]);
